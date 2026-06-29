import hashlib
import json
import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional

from django.conf import settings

from etl.client import OpenSearchClient
from etl.documents import (
    RawOpenAlexInputDocument,
    SilverDocument,
)
from etl.mapping_silver import SILVER_MAPPING
from etl.deduplicator.openalex import OpenAlexMatcher
from etl.deduplicator.scielo import SciELODeduplicator
from etl.models import EtlPipelineConfig
from etl.transform.merger import SilverMerger
from etl.transform.normalizers import (
    normalize_doi,
    normalize_openalex_id,
    normalize_text,
)
from etl.transform.standardizer import standardizer_for
from harvest.utils import clean_source_payload

logger = logging.getLogger(__name__)


class OpenSearchETLPipeline:
    """
    Main orchestrator for OpenSearch-based ETL pipeline.

    Processes input documents through deduplication, matching, merging,
    standardization, and indexing to silver indices.
    """

    def __init__(
        self,
        opensearch_url: str | None = None,
        opensearch_host: str | None = None,
        opensearch_port: int | None = None,
        input_scielo_index: str | None = None,
        input_openalex_index: str | None = None,
        public_alias: str = "silver_scientific_production",
        batch_size: int = 1000,
        pipeline_config: EtlPipelineConfig | None = None,
    ):
        self.opensearch_url = opensearch_url
        self.opensearch_host = opensearch_host
        self.opensearch_port = opensearch_port

        self.input_scielo_index = input_scielo_index or settings.ETL_INPUT_SCIELO_ARTICLES
        self.public_alias = public_alias

        self.batch_size = batch_size

        self.indexed_index_names: set[str] = set()
        self.loaded_source_ids: set[str] = set()

        self.pipeline_config = pipeline_config or EtlPipelineConfig.objects.get_for_source(self.input_scielo_index)
        self.document_type = self.pipeline_config.default_document_type
        self.input_openalex_index = self.pipeline_config.openalex_index_for(input_openalex_index)
        self.silver_index_pattern = getattr(
            settings,
            "ETL_SILVER_INDEX_PATTERN",
            "silver_scientific_production",
        )
        self.silver_write_alias = getattr(settings, "ETL_SILVER_WRITE_ALIAS", "silver_write")
        self.silver_bulk_max_docs = getattr(settings, "ETL_SILVER_BULK_MAX_DOCS", 1000)
        self.silver_bulk_max_bytes = getattr(settings, "ETL_SILVER_BULK_MAX_BYTES", 50 * 1024 * 1024)
        self.rules = self.pipeline_config.to_rules()

        self.client = OpenSearchClient(
            host=opensearch_host,
            port=opensearch_port,
            url=opensearch_url,
        )
        self.scielo_deduplicator = (
            SciELODeduplicator(rules=self.rules)
            if self.pipeline_config.deduplicate_scielo
            else None
        )
        self.openalex_matcher = OpenAlexMatcher(
            opensearch_host=opensearch_host,
            opensearch_port=opensearch_port,
            opensearch_url=opensearch_url,
            input_openalex_index=self.input_openalex_index,
            rules=self.rules,
        )
        self.merger = SilverMerger()
        self.skipped_doc_ids = []

    def run(
        self,
        max_docs: Optional[int] = None,
        year_filter: Optional[int] = None,
        doc_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        self.skipped_doc_ids = []
        self.indexed_index_names = set()

        result = {
            "status": "success",
            "total_input_docs": 0,
            "total_groups_formed": 0,
            "total_duplicates_found": 0,
            "total_merged_docs": 0,
            "total_indexed_docs": 0,
            "total_skipped_docs": 0,
            "skipped_doc_ids": [],
            "groups_with_openalex_matches": 0,
            "total_openalex_matches": 0,
            "scielo_dedup_source_ids": [],
            "openalex_matched_source_ids": [],
            "scielo_dedup_map": {},
            "openalex_match_map": {},
            "errors": 0,
            "warnings": 0,
            "error_messages": [],
            "warning_messages": [],
            "openalex_only_removed_after_merge": 0,
        }

        try:
            input_docs = self._load_scielo_input_documents(
                max_docs=max_docs,
                year_filter=year_filter,
                doc_ids=doc_ids,
            )
            result["total_input_docs"] = len(input_docs)

            if not input_docs:
                return self._finalize_result(result)

            groups = self._build_scielo_groups(input_docs)
            result["total_groups_formed"] = len(groups)
            result["total_duplicates_found"] = sum(
                len(group) - 1 for group in groups.values() if len(group) > 1
            )
            scielo_dedup_source_ids = []
            scielo_dedup_map: dict[str, list[str]] = {}
            for group in groups.values():
                if len(group) > 1:
                    group_pids = [
                        doc.get("code") or doc.get("pid_v2") or doc.get("id") or ""
                        for doc in group
                    ]
                    for doc in group:
                        os_id = doc.get("_os_id")
                        if os_id:
                            scielo_dedup_source_ids.append(os_id)
                            scielo_dedup_map[os_id] = [pid for pid in group_pids if pid]
            result["scielo_dedup_source_ids"] = scielo_dedup_source_ids
            result["scielo_dedup_map"] = scielo_dedup_map

            all_merged_docs = []

            for idx, (root_idx, group) in enumerate(groups.items(), 1):
                try:
                    openalex_matches = self.openalex_matcher.find_matches(
                        scielo_group=group,
                        max_candidates=3,
                    )

                    if openalex_matches:
                        result["groups_with_openalex_matches"] += 1
                        result["total_openalex_matches"] += len(openalex_matches)

                        oa_ids = [
                            self._openalex_ids_from_silver_doc(silver_doc)
                            for silver_doc, _strategy, _confidence, _validation in openalex_matches
                        ]

                        oa_ids = [oid for items in oa_ids for oid in items]
                        oa_ids = [oid for oid in oa_ids if oid]

                        for doc in group:
                            if os_id := doc.get("_os_id"):
                                result["openalex_matched_source_ids"].append(os_id)
                                result["openalex_match_map"][os_id] = oa_ids

                    scielo_silver_docs = []
                    for input_doc_data in group:
                        try:
                            input_doc = self._build_input_document(input_doc_data, source="scielo")
                            silver_doc = standardizer_for(input_doc).run(input_doc)
                            scielo_silver_docs.append(silver_doc)

                        except Exception as e:
                            result["warning_messages"].append(f"Standardization error: {e}")

                    if not scielo_silver_docs:
                        result["warning_messages"].append(
                            f"No standardized SciELO docs for group {idx}"
                        )
                        continue

                    merged_doc = self.merger.merge(
                        scielo_docs=scielo_silver_docs,
                        openalex_matches=openalex_matches,
                    )

                    all_merged_docs.append(merged_doc)
                    result["total_merged_docs"] += 1

                except Exception as e:
                    result["error_messages"].append(f"Group {idx} processing error: {str(e)}")

            indexed_count = self._index_silver_documents(all_merged_docs)
            result["total_indexed_docs"] = indexed_count
            result["total_skipped_docs"] = len(self.skipped_doc_ids)
            result["skipped_doc_ids"] = self.skipped_doc_ids

            removed_count = self._remove_openalex_only_placeholders(all_merged_docs)
            result["openalex_only_removed_after_merge"] = removed_count

        except Exception as e:
            logger.error(f"Pipeline failed: {e}", exc_info=True)
            result["error_messages"].append(f"Pipeline failure: {str(e)}")

        return self._finalize_result(result)

    def _load_scielo_input_documents(
        self,
        max_docs: Optional[int] = None,
        year_filter: Optional[int] = None,
        doc_ids: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        query = {"match_all": {}}

        filters = []
        if doc_ids:
            filters.append({"ids": {"values": [str(doc_id) for doc_id in doc_ids]}})
        if year_filter and not doc_ids:
            filters.append({"term": {"publication_year": year_filter}})
        if filters:
            query = {"bool": {"filter": filters}}

        page_size = min(max_docs, 1000) if max_docs else 1000
        search_body = {
            "query": query,
            "size": page_size,
        }

        self.loaded_source_ids = set()
        docs = []
        for hit, normalized in self._scroll_hits(self.input_scielo_index, search_body):
            if (
                self.pipeline_config.document_type_for_payload(normalized)
                != self.pipeline_config.default_document_type
            ):
                continue
            docs.append(normalized)
            self.loaded_source_ids.update(
                self._source_identity_values(hit.get("_id"), normalized)
            )

            if max_docs and len(docs) >= max_docs:
                docs = docs[:max_docs]
                break

        if doc_ids and docs:
            docs = self._expand_scielo_input_context(docs)

        if max_docs and len(docs) > max_docs:
            docs = docs[:max_docs]

        return docs

    def _finalize_result(self, result: dict) -> dict:
        result["errors"] = len(result["error_messages"])
        result["warnings"] = len(result["warning_messages"])

        if result["errors"]:
            result["status"] = "failed"

        elif result["total_input_docs"] == 0:
            result["status"] = "empty"

        return result

    def _build_scielo_groups(self, input_docs: List[Dict[str, Any]]) -> Dict[int, List[Dict[str, Any]]]:
        if not self.pipeline_config.deduplicate_scielo:
            return {idx: [doc] for idx, doc in enumerate(input_docs)}

        if self.scielo_deduplicator is None:
            raise RuntimeError("SciELO deduplicator is required for this target")

        return self.scielo_deduplicator.find_duplicates(articles=input_docs)

    def _expand_scielo_input_context(self, docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        field_values: dict[str, list] = defaultdict(list)

        for doc in docs:
            for identity_field in ("doi", "code", "id", "doc_id"):
                value = doc.get(identity_field)
                if value:
                    field_values[identity_field].append(value)

            ids = doc.get("ids") if isinstance(doc.get("ids"), dict) else {}
            for identity_field in ("scl_preprint_id", "dataset_id", "scl_book_id", "doi", "isbn"):
                value = ids.get(identity_field)
                if value:
                    field_values[f"ids.{identity_field}"].append(value)

                monograph = doc.get("monograph") or {}
                m_ids = monograph.get("ids")
                if isinstance(m_ids, dict):
                    m_value = m_ids.get(identity_field)
                    if m_value:
                        field_values[f"ids.{identity_field}"].append(m_value)
                        field_values[f"monograph.ids.{identity_field}"].append(m_value)
                        field_values[f"monograph.{identity_field}"].append(m_value)
                elif isinstance(monograph, dict):
                    m_value = monograph.get(identity_field)
                    if m_value:
                        field_values[f"monograph.{identity_field}"].append(m_value)

        should = [
            {"terms": {field: list(dict.fromkeys(values))}}
            for field, values in field_values.items()
            if values
        ]
        if not should:
            return docs

        search_body = {
            "query": {"bool": {"should": should, "minimum_should_match": 1}},
            "size": 1000,
        }

        combined = {json.dumps(doc, sort_keys=True, ensure_ascii=True): doc for doc in docs}

        for hit, normalized in self._scroll_hits(self.input_scielo_index, search_body):
            self.loaded_source_ids.update(
                self._source_identity_values(hit.get("_id"), normalized)
            )
            combined[json.dumps(normalized, sort_keys=True, ensure_ascii=True)] = normalized

        return list(combined.values())

    def _source_identity_values(
        self,
        hit_id: str | None,
        source: Dict[str, Any],
    ) -> set[str]:
        values = {
            hit_id,
            source.get("code"),
            source.get("id"),
            source.get("doc_id"),
        }

        ids = source.get("ids") if isinstance(source.get("ids"), dict) else {}
        for identity_field in ("scl_preprint_id", "dataset_id", "scl_book_id", "doi", "isbn"):
            values.add(ids.get(identity_field))

        monograph = source.get("monograph") or {}
        m_ids = monograph.get("ids")
        if isinstance(m_ids, dict):
            for identity_field in ("scl_preprint_id", "dataset_id", "scl_book_id", "doi", "isbn"):
                values.add(m_ids.get(identity_field))
        if isinstance(monograph, dict):
            for identity_field in ("scl_preprint_id", "dataset_id", "scl_book_id", "doi", "isbn"):
                values.add(monograph.get(identity_field))

        return {str(value) for value in values if value not in (None, "")}

    def _scroll_hits(self, index: str, body: dict, scroll: str = "5m"):
        response = self.client.client.search(index=index, body=body, scroll=scroll)
        scroll_id = response.get("_scroll_id")
        try:
            while True:
                hits = response["hits"]["hits"]
                if not hits:
                    break
                for hit in hits:
                    normalized = clean_source_payload(hit["_source"])
                    normalized["_os_id"] = hit.get("_id")
                    yield hit, normalized
                response = self.client.client.scroll(scroll_id=scroll_id, scroll=scroll)
                scroll_id = response.get("_scroll_id")
        finally:
            if scroll_id:
                self.client.client.clear_scroll(scroll_id=scroll_id)

    def _build_input_document(
        self,
        raw_data: Dict[str, Any],
        source: str = "scielo",
    ):
        if source == "scielo":
            doc_cls = self.pipeline_config.input_document_class()
            return doc_cls.from_raw(
                raw_data,
                doc_type_fn=self.pipeline_config.document_type_for_payload,
                fallback_id_fn=self._stable_fallback_doc_id,
            )
        elif source == "openalex":
            return RawOpenAlexInputDocument.from_raw(raw_data)
        else:
            raise ValueError(f"Unknown source: {source}")

    def _index_silver_documents(
        self,
        silver_docs: List[SilverDocument],
    ) -> int:
        if not silver_docs:
            return 0

        docs_to_index = []
        for doc in silver_docs:
            if not doc.publication_year:
                self.skipped_doc_ids.append(doc.doc_id)
                continue
            docs_to_index.append(doc)

        if not docs_to_index:
            return 0

        index_docs = self._prepare_silver_index_documents(docs_to_index)
        return self._write_silver_documents(index_docs)

    def _prepare_silver_index_documents(
        self,
        docs_to_index: List[SilverDocument],
    ) -> list[tuple[str, SilverDocument]]:
        docs_by_id: dict[str, list[SilverDocument]] = defaultdict(list)
        for doc in docs_to_index:
            docs_by_id[doc.doc_id].append(doc)

        index_docs: list[tuple[str, SilverDocument]] = []
        for doc_id, docs in docs_by_id.items():
            if len(docs) == 1:
                index_docs.append((doc_id, docs[0]))
                continue

            if self._silver_docs_can_share_index_id(docs):
                merged_doc = self._merge_compatible_silver_docs(docs)
                index_docs.append((merged_doc.doc_id, merged_doc))
                continue

            ranked_docs = sorted(
                enumerate(docs),
                key=lambda item: (
                    len(self._openalex_ids_from_silver_doc(item[1])),
                    len(item[1].title_with_lang or []),
                    1 if self._normalized_silver_doi(item[1]) else 0,
                    -item[0],
                ),
                reverse=True,
            )
            ordered_docs = [doc for _idx, doc in ranked_docs]
            logger.warning(
                "Conflicting silver documents share doc_id %s; keeping one on the "
                "canonical _id and assigning alternate _ids to %s document(s)",
                doc_id,
                len(ordered_docs) - 1,
            )
            index_docs.append((doc_id, ordered_docs[0]))
            for doc in ordered_docs[1:]:
                digest = hashlib.sha256(
                    json.dumps(
                        doc.to_index_dict(),
                        sort_keys=True,
                        ensure_ascii=True,
                    ).encode("utf-8")
                ).hexdigest()
                index_docs.append((f"{doc.doc_id}__{digest[:12]}", doc))

        return index_docs

    def _silver_docs_can_share_index_id(
        self,
        docs: list[SilverDocument],
    ) -> bool:
        doc_dois = [self._normalized_silver_doi(doc) for doc in docs]
        known_dois = {doi for doi in doc_dois if doi}

        if len(known_dois) > 1:
            return False
        if len(known_dois) == 1 and all(doc_dois):
            return True

        title_sets = []
        for doc in docs:
            title_values = set()
            if normalized := normalize_text(doc.title):
                title_values.add(normalized.lower())

            for item in doc.title_with_lang or []:
                if not isinstance(item, dict):
                    continue
                title = item.get("title") or item.get("text")
                if normalized := normalize_text(title):
                    title_values.add(normalized.lower())

            if title_values:
                title_sets.append(title_values)

        if len(title_sets) < 2:
            return True

        return bool(set.intersection(*title_sets))

    def _normalized_silver_doi(self, doc: SilverDocument) -> str | None:
        ids = doc.ids if isinstance(doc.ids, dict) else {}
        raw_doi = doc.doi or ids.get("doi")
        if isinstance(raw_doi, list):
            raw_doi = raw_doi[0] if raw_doi else None
        return normalize_doi(raw_doi)

    def _merge_compatible_silver_docs(
        self,
        docs: list[SilverDocument],
    ) -> SilverDocument:
        merged = self.merger.merge(scielo_docs=docs, openalex_matches=[])
        data = merged.to_dict()

        openalex_ids = []
        openalex_lang_items = []
        openalex_match_details = []
        for doc in docs:
            indexed = doc.to_index_dict()
            ids = indexed.get("ids") or {}
            openalex_ids.extend(self._openalex_ids_from_silver_doc(doc))
            openalex_lang_items.extend(ids.get("openalex_with_lang") or [])
            trace = (indexed.get("oca_data") or {}).get("merge_trace") or {}
            openalex_match_details.extend(trace.get("openalex_matches") or [])

        openalex_ids = list(dict.fromkeys(openalex_ids))
        if openalex_ids:
            data.setdefault("ids", {})["openalex"] = openalex_ids
            data["openalex_id"] = openalex_ids[0]
            openalex = dict(data.setdefault("oca_data", {}).get("openalex") or {})
            openalex["ids"] = openalex_ids
            data["oca_data"]["openalex"] = openalex
            data["oca_data"]["scope"] = list(
                dict.fromkeys(
                    (data["oca_data"].get("scope") or []) + ["scielo", "openalex"]
                )
            )

        if openalex_lang_items:
            keyed_items = {
                (item.get("language"), item.get("openalex")): item
                for item in openalex_lang_items
                if isinstance(item, dict) and item.get("language") and item.get("openalex")
            }
            data.setdefault("ids", {})["openalex_with_lang"] = list(keyed_items.values())

        if openalex_match_details:
            trace = data.setdefault("oca_data", {}).setdefault("merge_trace", {})
            keyed_matches = {
                item.get("doc_id"): item
                for item in openalex_match_details
                if isinstance(item, dict) and item.get("doc_id")
            }
            trace["openalex_matches"] = list(keyed_matches.values())

        return SilverDocument(**data)

    def _write_silver_documents(
        self,
        docs_to_index: list[tuple[str, SilverDocument]],
    ) -> int:
        index_prefix = self.silver_index_pattern
        write_alias = self.silver_write_alias
        bootstrap_index = self.client.ensure_rollover_index(
            index_prefix=index_prefix,
            write_alias=write_alias,
            public_alias=self.public_alias,
            mapping=SILVER_MAPPING,
        )

        for actions in self._silver_bulk_action_chunks(docs_to_index, write_alias):
            self._execute_bulk_index(actions, write_alias)
        if bootstrap_index:
            self.indexed_index_names.add(bootstrap_index)

        rollover_index = self.client.rollover(
            write_alias=write_alias,
            public_alias=self.public_alias,
            mapping=SILVER_MAPPING,
            max_size=getattr(settings, "ETL_SILVER_ROLLOVER_MAX_SIZE", None)
        )
        if rollover_index:
            self.indexed_index_names.add(rollover_index)
        if not self.indexed_index_names:
            self.indexed_index_names.add(write_alias)

        return len(docs_to_index)

    def _silver_bulk_action_chunks(
        self,
        docs_to_index: list[tuple[str, SilverDocument]],
        write_alias: str,
    ):
        max_docs = max(int(self.silver_bulk_max_docs or 1), 1)
        max_bytes = max(int(self.silver_bulk_max_bytes or 1), 1)

        actions = []
        chunk_docs = 0
        chunk_bytes = 0

        for index_id, doc in docs_to_index:
            action = {
                "index": {
                    "_index": write_alias,
                    "_id": index_id,
                }
            }
            source = doc.to_index_dict()
            action_bytes = self._bulk_action_size_bytes(action, source)

            if actions and (chunk_docs >= max_docs or chunk_bytes + action_bytes > max_bytes):
                yield actions
                actions = []
                chunk_docs = 0
                chunk_bytes = 0

            actions.extend([action, source])
            chunk_docs += 1
            chunk_bytes += action_bytes

        if actions:
            yield actions

    def _bulk_action_size_bytes(self, action: dict, source: dict) -> int:
        return (
            len(json.dumps(action, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
            + len(json.dumps(source, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
            + 2
        )

    def _execute_bulk_index(self, actions: list[dict], target_name: str) -> None:
        response = self.client.client.bulk(body=actions)

        if response.get("errors"):
            error_items = [
                item.get("index", {})
                for item in response["items"]
                if item.get("index", {}).get("status", 200) >= 400
            ]
            error_count = len(error_items)
            first_error = error_items[0].get("error") if error_items else None
            raise RuntimeError(
                f"Bulk indexing failed for {error_count} documents in {target_name}: "
                f"{first_error}"
            )

    def _stable_fallback_doc_id(self, raw_data: Dict[str, Any]) -> str:
        source_payload = {
            "title": str(raw_data.get("title") or ""),
            "publication_year": raw_data.get("publication_year"),
            "journal_title": raw_data.get("journal_title"),
            "source_index": self.input_scielo_index,
        }
        digest = hashlib.sha256(
            json.dumps(source_payload, sort_keys=True, ensure_ascii=True).encode("utf-8")
        ).hexdigest()
        return f"doc_{digest[:20]}"

    def _remove_openalex_only_placeholders(
        self,
        merged_docs: list[SilverDocument],
    ) -> int:
        openalex_only_pattern = getattr(
            settings,
            "ETL_OPENALEX_ONLY_INDEX_PATTERN",
            "silver_openalex",
        )
        index_pattern = f"{openalex_only_pattern}-*"

        if not self.client.index_exists(index_pattern):
            return 0

        oa_ids: set[str] = set()
        for doc in merged_docs:
            if doc.doc_id in self.skipped_doc_ids:
                continue
            found_ids = self._openalex_ids_from_silver_doc(doc)
            oa_ids.update(found_ids)

        if not oa_ids:
            return 0

        ids_list = list(oa_ids)
        total_removed = 0
        chunk_size = 10000
        for i in range(0, len(ids_list), chunk_size):
            chunk = ids_list[i:i + chunk_size]
            try:
                resp = self.client.client.delete_by_query(
                    index=index_pattern,
                    body={"query": {"ids": {"values": chunk}}},
                    refresh=True,
                )
                deleted = resp.get("deleted", 0)
                total_removed += deleted
            except Exception as e:
                logger.warning(
                    "Error removing OpenAlex-only docs from %s: %s",
                    index_pattern,
                    e,
                )

        return total_removed

    def _openalex_ids_from_silver_doc(self, doc: SilverDocument) -> list[str]:
        oa_ids: list[str] = []

        doc_dict = doc.to_index_dict()
        ids_field = doc_dict.get("ids", {})
        oa_field = ids_field.get("openalex") if isinstance(ids_field, dict) else None
        if oa_field:
            items = oa_field if isinstance(oa_field, list) else [oa_field]
            for item in items:
                if normalized := normalize_openalex_id(item):
                    if normalized not in oa_ids:
                        oa_ids.append(normalized)

        oca_data = doc_dict.get("oca_data", {})
        oca_openalex = oca_data.get("openalex", {})
        oca_ids_list = oca_openalex.get("ids") if isinstance(oca_openalex, dict) else None
        if oca_ids_list and isinstance(oca_ids_list, list):
            for item in oca_ids_list:
                if normalized := normalize_openalex_id(item):
                    if normalized not in oa_ids:
                        oa_ids.append(normalized)

        return oa_ids
