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
        silver_index_pattern: str | None = None,
        public_alias: str = "scientific_production",
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
        self.silver_index_pattern = silver_index_pattern or self.pipeline_config.silver_index_pattern
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

        logger.info("OpenSearchETLPipeline initialized")
        logger.info("  Input SciELO index: %s", self.input_scielo_index)
        logger.info("  Input OpenAlex index: %s", self.input_openalex_index)
        logger.info("  Silver index pattern: %s", self.silver_index_pattern)
        logger.info("  Batch size: %s", self.batch_size)

    def run(
        self,
        max_docs: Optional[int] = None,
        year_filter: Optional[int] = None,
        doc_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        result = {
            "status": "success",
            "total_input_docs": 0,
            "total_groups_formed": 0,
            "total_duplicates_found": 0,
            "total_merged_docs": 0,
            "total_indexed_docs": 0,
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
        }

        logger.info("=" * 80)
        logger.info("STARTING OPENSEARCH ETL PIPELINE")
        logger.info("=" * 80)

        try:
            logger.info("\n[Step 1] Loading input documents...")
            input_docs = self._load_scielo_input_documents(
                max_docs=max_docs,
                year_filter=year_filter,
                doc_ids=doc_ids,
            )
            result["total_input_docs"] = len(input_docs)
            logger.info(f"Loaded {len(input_docs)} input documents")

            if not input_docs:
                logger.warning("No documents to process")
                return self._finalize_result(result)

            logger.info("\n[Step 2] Building SciELO document groups...")
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
            logger.info(
                f"Grouping complete: {len(input_docs)} docs -> "
                f"{len(groups)} groups ({result['total_duplicates_found']} duplicates)"
            )

            logger.info("\n[Step 3] Processing document groups...")
            all_merged_docs = []

            for idx, (root_idx, group) in enumerate(groups.items(), 1):
                try:
                    logger.debug(
                        f"Processing group {idx}/{len(groups)} ({len(group)} doc(s))"
                    )

                    openalex_matches = self.openalex_matcher.find_matches(
                        scielo_group=group,
                        max_candidates=3,
                    )

                    if openalex_matches:
                        result["groups_with_openalex_matches"] += 1
                        result["total_openalex_matches"] += len(openalex_matches)
                        oa_ids = [
                            match[0].get("id") or match[0].get("openalex_id")
                            for match in openalex_matches
                        ]
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
                            logger.warning(f"Error standardizing SciELO doc: {e}")
                            result["warning_messages"].append(f"Standardization error: {e}")

                    if not scielo_silver_docs:
                        logger.warning(f"No standardized SciELO docs for group {idx}")
                        continue

                    openalex_silver_matches = []
                    for oa_doc, strategy, confidence, validation in openalex_matches:
                        try:
                            input_oa = self._build_input_document(oa_doc, source="openalex")
                            silver_oa = standardizer_for(input_oa).run(input_oa)
                            openalex_silver_matches.append(
                                (
                                    silver_oa,
                                    strategy,
                                    confidence,
                                    validation
                                )
                            )
                        
                        except Exception as e:
                            logger.warning(f"Error standardizing OpenAlex doc: {e}")
                            result["warning_messages"].append(
                                f"OpenAlex standardization error: {e}"
                            )

                    merged_doc = self.merger.merge(
                        scielo_docs=scielo_silver_docs,
                        openalex_matches=openalex_silver_matches,
                    )

                    all_merged_docs.append(merged_doc)
                    result["total_merged_docs"] += 1

                except Exception as e:
                    logger.error(f"Error processing group {idx}: {e}", exc_info=True)
                    result["error_messages"].append(f"Group {idx} processing error: {str(e)}")

            logger.info("\n[Step 4] Indexing to silver indices...")
            indexed_count = self._index_silver_documents(all_merged_docs)
            result["total_indexed_docs"] = indexed_count
            logger.info(f"Indexed {indexed_count} documents to silver indices")

            logger.info("\n" + "=" * 80)
            logger.info("PIPELINE EXECUTION COMPLETE")
            logger.info("=" * 80)

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
        if year_filter:
            filters.append({"term": {"publication_year": year_filter}})
        if filters:
            query = {"bool": {"filter": filters}}

        page_size = min(max_docs, 1000) if max_docs else 1000
        search_body = {
            "query": query,
            "size": page_size,
        }

        logger.info(f"Loading documents from {self.input_scielo_index}...")
        if year_filter:
            logger.info(f"  Year filter: {year_filter}")
        if max_docs:
            logger.info(f"  Max docs: {max_docs}")

        self.loaded_source_ids = set()
        response = self.client.client.search(
            index=self.input_scielo_index,
            body=search_body,
            scroll="5m",
        )

        scroll_id = response.get("_scroll_id")
        docs = []
        try:
            while True:
                hits = response["hits"]["hits"]
                if not hits:
                    break

                for hit in hits:
                    normalized = clean_source_payload(hit["_source"])
                    if (
                        self.pipeline_config.document_type_for_payload(normalized)
                        != self.pipeline_config.default_document_type
                    ):
                        continue
                    normalized["_os_id"] = hit.get("_id")
                    docs.append(normalized)
                    self.loaded_source_ids.update(
                        self._source_identity_values(hit.get("_id"), normalized)
                    )

                if max_docs and len(docs) >= max_docs:
                    docs = docs[:max_docs]
                    break

                response = self.client.client.scroll(scroll_id=scroll_id, scroll="5m")
                scroll_id = response.get("_scroll_id")
        
        finally:
            if scroll_id:
                self.client.client.clear_scroll(scroll_id=scroll_id)

        if doc_ids and docs:
            docs = self._expand_scielo_input_context(docs)

        if max_docs and len(docs) > max_docs:
            docs = docs[:max_docs]

        logger.info(f"Loaded {len(docs)} documents")
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
            for identity_field in ("scl_preprint_id", "dataset_id", "doi"):
                value = ids.get(identity_field)
                if value:
                    field_values[f"ids.{identity_field}"].append(value)

        should = [
            {"terms": {field: list(dict.fromkeys(values))}}
            for field, values in field_values.items()
            if values
        ]
        if not should:
            return docs

        response = self.client.client.search(
            index=self.input_scielo_index,
            body={
                "query": {"bool": {"should": should, "minimum_should_match": 1}},
                "size": max(100, len(docs) * 10),
            },
        )

        combined = {}
        for doc in docs:
            combined[str(doc)] = doc

        for hit in response["hits"]["hits"]:
            normalized = clean_source_payload(hit["_source"])
            normalized["_os_id"] = hit.get("_id")
            self.loaded_source_ids.update(
                self._source_identity_values(hit.get("_id"), normalized)
            )
            combined[str(normalized)] = normalized

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
        for identity_field in ("scl_preprint_id", "dataset_id", "doi"):
            values.add(ids.get(identity_field))

        return {str(value) for value in values if value not in (None, "")}

    def _build_input_document(
        self,
        raw_data: Dict[str, Any],
        source: str = "scielo",
    ):
        if source == "scielo":
            input_cls = self.pipeline_config.input_document_class()
            return input_cls.from_raw(
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
        """
        Index silver documents to year-partitioned indices.

        Args:
            silver_docs: List of standardized silver documents

        Returns:
            Number of documents successfully indexed
        """
        if not silver_docs:
            return 0

        docs_by_year = {}
        for doc in silver_docs:
            year = doc.publication_year
            if not year:
                logger.warning(f"Document missing publication_year: {doc.doc_id}")
                continue

            if year not in docs_by_year:
                docs_by_year[year] = []
            docs_by_year[year].append(doc)

        total_indexed = 0

        for year, docs in docs_by_year.items():
            index_name = self._silver_index_name(year)
            logger.info(f"Indexing {len(docs)} documents to {index_name}...")
            self.client.create_index(index_name, SILVER_MAPPING)

            actions = []
            for doc in docs:
                actions.append(
                    {
                        "index": {
                            "_index": index_name,
                            "_id": doc.doc_id,
                        }
                    }
                )
                actions.append(doc.to_index_dict())

            try:
                response = self.client.client.bulk(body=actions)

                if response.get("errors"):
                    error_items = [
                        item.get("index", {})
                        for item in response["items"]
                        if item.get("index", {}).get("status", 200) >= 400
                    ]
                    error_count = len(error_items)
                    logger.error(f"Bulk indexing had {error_count} errors")
                    stats_errors = [item.get("error") for item in error_items]
                    for err in stats_errors[:5]:
                        logger.error(f"  Index error: {err}")
                    total_indexed += len(docs) - error_count
                    raise RuntimeError(
                        f"Bulk indexing failed for {error_count} documents in {index_name}"
                    )
                else:
                    logger.info(f"Successfully indexed {len(docs)} documents")
                    total_indexed += len(docs)

                self.client.add_alias(index_name, self.public_alias)
                self.indexed_index_names.add(index_name)

            except RuntimeError:
                raise
            except Exception as e:
                logger.error(f"Failed to index to {index_name}: {e}")
                raise

        return total_indexed

    def _silver_index_name(self, year: int) -> str:
        if "{year}" in self.silver_index_pattern:
            return self.silver_index_pattern.format(year=year)
        return self.silver_index_pattern

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
