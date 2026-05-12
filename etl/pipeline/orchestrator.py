import hashlib
import json
import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional

from django.conf import settings

from etl.indexing.client import OpenSearchClient
from etl.documents import BronzeDocument, SilverDocument
from etl.indexing.schema import SILVER_MAPPING
from etl.pipeline.deduplicator import OpenAlexMatcher, SciELODeduplicator, extract_doi
from etl.pipeline.defaults import get_pipeline_target
from etl.pipeline.strategies import get_strategy
from harvest.utils import clean_source_payload

logger = logging.getLogger(__name__)


def _empty_pipeline_result() -> Dict[str, Any]:
    return {
        "status": "success",
        "total_bronze_docs": 0,
        "total_groups_formed": 0,
        "total_duplicates_found": 0,
        "total_merged_docs": 0,
        "total_indexed_docs": 0,
        "groups_with_openalex_matches": 0,
        "total_openalex_matches": 0,
        "errors": 0,
        "warnings": 0,
        "error_messages": [],
        "warning_messages": [],
    }


def _finalize_pipeline_result(result: Dict[str, Any]) -> Dict[str, Any]:
    result["errors"] = len(result["error_messages"])
    result["warnings"] = len(result["warning_messages"])

    if result["errors"]:
        result["status"] = "failed"
    elif result["total_bronze_docs"] == 0:
        result["status"] = "empty"
    return result


class OpenSearchETLPipeline:
    """
    Main orchestrator for OpenSearch-based ETL pipeline.

    Processes bronze documents through deduplication, matching, merging,
    standardization, and indexing to silver indices.
    """

    def __init__(
        self,
        opensearch_url: str | None = None,
        opensearch_host: str | None = None,
        opensearch_port: int | None = None,
        bronze_scielo_index: str | None = None,
        bronze_openalex_index: str | None = None,
        silver_index_pattern: str | None = None,
        public_alias: str = "scientific_production",
        batch_size: int = 1000,
    ):
        """
        Initialize the ETL pipeline.

        Args:
            opensearch_url: Complete OpenSearch URL from Django settings.
            opensearch_host: OpenSearch host.
            opensearch_port: OpenSearch port.
            bronze_scielo_index: Source index for SciELO articles
            bronze_openalex_index: Source index for OpenAlex works
            silver_index_pattern: Target index name or pattern. If it includes
                {year}, documents are partitioned by publication year.
            public_alias: OpenSearch alias consumed by SCMS applications.
            batch_size: Number of documents to process per batch
        """
        self.opensearch_url = opensearch_url
        self.opensearch_host = opensearch_host
        self.opensearch_port = opensearch_port
        self.bronze_scielo_index = bronze_scielo_index or settings.ETL_BRONZE_SCIELO_ARTICLES
        self.bronze_openalex_index = bronze_openalex_index or settings.ETL_RAW_OPENALEX_WORKS
        self.silver_index_pattern = silver_index_pattern or settings.ETL_SILVER_ARTICLE_PATTERN
        self.public_alias = public_alias
        self.batch_size = batch_size
        self.indexed_index_names: set[str] = set()
        self.loaded_source_ids: set[str] = set()

        self.target = get_pipeline_target(self.bronze_scielo_index)
        self.document_type = self.target.document_type

        self.client = OpenSearchClient(
            host=opensearch_host,
            port=opensearch_port,
            url=opensearch_url,
        )
        self.scielo_deduplicator = SciELODeduplicator(
            rules=self.target.rules,
        )
        self.openalex_matcher = OpenAlexMatcher(
            opensearch_host=opensearch_host,
            opensearch_port=opensearch_port,
            opensearch_url=opensearch_url,
            bronze_openalex_index=self.bronze_openalex_index,
            rules=self.target.rules,
        )

        logger.info("OpenSearchETLPipeline initialized")
        logger.info("  Bronze SciELO index: %s", self.bronze_scielo_index)
        logger.info("  Bronze OpenAlex index: %s", self.bronze_openalex_index)
        logger.info("  Silver index pattern: %s", self.silver_index_pattern)
        logger.info("  Batch size: %s", self.batch_size)

    def run(
        self,
        max_docs: Optional[int] = None,
        year_filter: Optional[int] = None,
        doc_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Run the full ETL pipeline.

        Args:
            max_docs: Maximum number of documents to process (None = all)
            year_filter: Only process articles from specific year (None = all years)

        Returns:
            Operational result with counters and error details.
        """
        result = _empty_pipeline_result()

        logger.info("=" * 80)
        logger.info("STARTING OPENSEARCH ETL PIPELINE")
        logger.info("=" * 80)

        try:
            logger.info("\n[Step 1] Loading bronze documents...")
            bronze_docs = self._load_bronze_documents(
                max_docs=max_docs,
                year_filter=year_filter,
                doc_ids=doc_ids,
            )
            result["total_bronze_docs"] = len(bronze_docs)
            logger.info(f"Loaded {len(bronze_docs)} bronze documents")

            if not bronze_docs:
                logger.warning("No documents to process")
                return _finalize_pipeline_result(result)

            logger.info("\n[Step 2] Running SciELO deduplication...")
            groups = self.scielo_deduplicator.find_duplicates(
                articles=bronze_docs,
            )
            result["total_groups_formed"] = len(groups)
            result["total_duplicates_found"] = sum(
                len(group) - 1 for group in groups.values() if len(group) > 1
            )
            logger.info(
                f"Deduplication complete: {len(bronze_docs)} docs -> "
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

                    scielo_silver_docs = []
                    for bronze_doc_data in group:
                        try:
                            bronze_doc = self._create_bronze_document(
                                bronze_doc_data, source="scielo"
                            )
                            silver_doc = get_strategy(bronze_doc.document_type).standardizer.run(bronze_doc)
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
                            bronze_oa = self._create_bronze_document(
                                oa_doc, source="openalex"
                            )
                            silver_oa = get_strategy(bronze_oa.document_type).standardizer.run(bronze_oa)
                            openalex_silver_matches.append(
                                (silver_oa, strategy, confidence, validation)
                            )
                        except Exception as e:
                            logger.warning(f"Error standardizing OpenAlex doc: {e}")
                            result["warning_messages"].append(
                                f"OpenAlex standardization error: {e}"
                            )

                    strategy = get_strategy(scielo_silver_docs[0].type)
                    merged_doc = strategy.merger(
                        scielo_docs=scielo_silver_docs,
                        openalex_matches=openalex_silver_matches,
                        rules=strategy.rules,
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

        return _finalize_pipeline_result(result)

    def _load_bronze_documents(
        self,
        max_docs: Optional[int] = None,
        year_filter: Optional[int] = None,
        doc_ids: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Load bronze documents from OpenSearch with optional filtering.

        Uses scroll API for efficient large dataset retrieval.
        """
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

        logger.info(f"Loading documents from {self.bronze_scielo_index}...")
        if year_filter:
            logger.info(f"  Year filter: {year_filter}")
        if max_docs:
            logger.info(f"  Max docs: {max_docs}")

        self.loaded_source_ids = set()
        response = self.client.client.search(
            index=self.bronze_scielo_index,
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
            docs = self._expand_bronze_context(docs)

        if max_docs and len(docs) > max_docs:
            docs = docs[:max_docs]

        logger.info(f"Loaded {len(docs)} documents")
        return docs

    def _expand_bronze_context(self, docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
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
            index=self.bronze_scielo_index,
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

    def _create_bronze_document(
        self,
        raw_data: Dict[str, Any],
        source: str = "scielo",
    ) -> BronzeDocument:
        """
        Create a BronzeDocument from raw data.

        Handles different document types (articles, books, datasets, etc.)
        by extracting the appropriate ID field for each type.

        Args:
            raw_data: Raw document data from OpenSearch
            source: 'scielo' or 'openalex'

        Returns:
            BronzeDocument instance
        """
        if source == "scielo":
            doc_id = (
                raw_data.get("code")  # Articles
                or raw_data.get("id")  # Books
                or raw_data.get("doc_id")  # Generic
                or (
                    raw_data.get("ids", {}).get("scl_preprint_id")
                    if isinstance(raw_data.get("ids"), dict)
                    else None
                )  # Preprints
                or (
                    raw_data.get("ids", {}).get("dataset_id")
                    if isinstance(raw_data.get("ids"), dict)
                    else None
                )  # Datasets
                or self._stable_fallback_doc_id(raw_data)
            )

            publication_year = raw_data.get("publication_year")

            if publication_year:
                try:
                    publication_year = int(publication_year)
                except (ValueError, TypeError):
                    publication_year = None

            return BronzeDocument(
                doc_id=doc_id,
                document_type=self.target.document_type_for(raw_data),
                doi=extract_doi(raw_data),
                raw_scielo_data=raw_data,
                publication_year=publication_year,
            )

        elif source == "openalex":
            doc_id = raw_data.get("id")
            publication_year = raw_data.get("publication_year")

            if publication_year:
                try:
                    publication_year = int(publication_year)
                except (ValueError, TypeError):
                    publication_year = None

            return BronzeDocument(
                doc_id=doc_id,
                document_type=raw_data.get("type") or "article",
                doi=extract_doi(raw_data),
                raw_openalex_data=raw_data,
                publication_year=publication_year,
            )

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
            "source_index": self.bronze_scielo_index,
        }
        digest = hashlib.sha256(
            json.dumps(source_payload, sort_keys=True, ensure_ascii=True).encode("utf-8")
        ).hexdigest()
        return f"doc_{digest[:20]}"
