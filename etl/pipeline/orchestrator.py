import hashlib
import json
import logging
from typing import Any

from django.conf import settings

from etl.extractors import extract_doi
from etl.indexing.contracts import BronzeDocument, SilverDocument
from etl.indexing.schema import SILVER_MAPPING
from etl.pipeline.defaults import PipelineTarget
from etl.pipeline.standardizer import DefaultStandardizer
from etl.normalizers import int_or_none
from search_gateway.opensearch import OpenSearchIndexClient

logger = logging.getLogger(__name__)


def empty_pipeline_result() -> dict[str, Any]:
    return {
        "status": "success",
        "total_bronze_docs": 0,
        "total_standardized_docs": 0,
        "total_indexed_docs": 0,
        "errors": 0,
        "error_messages": [],
    }


class SilverETLPipeline:
    def __init__(
        self,
        target: PipelineTarget,
        *,
        opensearch_url: str | None = None,
        public_alias: str | None = None,
        batch_size: int | None = None,
        standardizer: DefaultStandardizer | None = None,
    ):
        self.target = target
        self.public_alias = public_alias or settings.ETL_PUBLIC_ALIAS
        self.batch_size = batch_size or settings.ETL_DEFAULT_BATCH_SIZE
        self.standardizer = standardizer or DefaultStandardizer()
        self.client = OpenSearchIndexClient(url=opensearch_url)
        self.indexed_index_names: set[str] = set()
        self.loaded_source_ids: set[str] = set()

    def run(
        self,
        *,
        max_docs: int | None = None,
        year_filter: int | None = None,
        doc_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        result = empty_pipeline_result()
        try:
            bronze_sources = self._load_bronze_documents(
                max_docs=max_docs,
                year_filter=year_filter,
                doc_ids=doc_ids,
            )
            result["total_bronze_docs"] = len(bronze_sources)
            if not bronze_sources:
                result["status"] = "empty"
                return result

            silver_docs = [
                self.standardizer.run(self._create_bronze_document(raw_data))
                for raw_data in bronze_sources
            ]
            result["total_standardized_docs"] = len(silver_docs)
            result["total_indexed_docs"] = self._index_silver_documents(silver_docs)
        except Exception as exc:
            logger.exception("Silver ETL pipeline failed")
            result["status"] = "failed"
            result["error_messages"].append(str(exc))
            result["errors"] = len(result["error_messages"])
        return result

    def _load_bronze_documents(
        self,
        *,
        max_docs: int | None = None,
        year_filter: int | None = None,
        doc_ids: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        query: dict[str, Any] = {"match_all": {}}
        filters = []
        if doc_ids:
            filters.append({"ids": {"values": [str(doc_id) for doc_id in doc_ids]}})
        if year_filter:
            filters.append({"term": {"publication_year": year_filter}})
        if filters:
            query = {"bool": {"filter": filters}}

        page_size = min(max_docs, self.batch_size) if max_docs else self.batch_size
        response = self.client.client.search(
            index=self.target.source_index,
            body={"query": query, "size": page_size},
            scroll="5m",
        )
        scroll_id = response.get("_scroll_id")
        docs = []
        self.loaded_source_ids = set()
        try:
            while True:
                hits = response["hits"]["hits"]
                if not hits:
                    break
                for hit in hits:
                    payload = self._source_payload(hit["_source"])
                    docs.append(payload)
                    self.loaded_source_ids.update(self._source_identity_values(hit.get("_id"), payload))
                    if max_docs and len(docs) >= max_docs:
                        return docs[:max_docs]

                response = self.client.client.scroll(scroll_id=scroll_id, scroll="5m")
                scroll_id = response.get("_scroll_id")
        finally:
            if scroll_id:
                self.client.client.clear_scroll(scroll_id=scroll_id)
        return docs

    def _source_payload(self, source: dict[str, Any]) -> dict[str, Any]:
        if isinstance(source.get("raw_data"), dict):
            return source["raw_data"]
        return {
            key: value
            for key, value in source.items()
            if key not in {"oca_indexed_at", "oca_source_hash"}
        }

    def _source_identity_values(self, hit_id: str | None, source: dict[str, Any]) -> set[str]:
        values = {hit_id, source.get("code"), source.get("id"), source.get("doc_id")}
        ids = source.get("ids") if isinstance(source.get("ids"), dict) else {}
        for key in ("scl_preprint_id", "dataset_id", "doi"):
            values.add(ids.get(key))
        return {str(value) for value in values if value not in (None, "")}

    def _create_bronze_document(self, raw_data: dict[str, Any]) -> BronzeDocument:
        return BronzeDocument(
            doc_id=self._source_doc_id(raw_data),
            document_type=self.target.document_type,
            source="scielo",
            raw_data=raw_data,
            publication_year=int_or_none(raw_data.get("publication_year")),
            publication_date=raw_data.get("publication_date"),
            doi=extract_doi(raw_data),
        )

    def _source_doc_id(self, raw_data: dict[str, Any]) -> str:
        ids = raw_data.get("ids") if isinstance(raw_data.get("ids"), dict) else {}
        return str(
            raw_data.get("code")
            or raw_data.get("id")
            or raw_data.get("doc_id")
            or ids.get("scl_preprint_id")
            or ids.get("dataset_id")
            or self._stable_fallback_doc_id(raw_data)
        )

    def _index_silver_documents(self, silver_docs: list[SilverDocument]) -> int:
        docs_by_index: dict[str, list[SilverDocument]] = {}
        for doc in silver_docs:
            index_name = self.target.silver_index_name(doc.publication_year)
            docs_by_index.setdefault(index_name, []).append(doc)

        indexed = 0
        for index_name, docs in docs_by_index.items():
            self.client.create_index(index_name, SILVER_MAPPING)
            actions = []
            for doc in docs:
                actions.append({"index": {"_index": index_name, "_id": doc.doc_id}})
                actions.append(doc.to_index_dict())

            response = self.client.client.bulk(body=actions)
            if response.get("errors"):
                error_count = sum(
                    1
                    for item in response.get("items", [])
                    if item.get("index", {}).get("status", 200) >= 400
                )
                raise RuntimeError(f"Bulk indexing failed for {error_count} documents in {index_name}")

            indexed += len(docs)
            self.client.add_alias(index_name, self.public_alias)
            self.indexed_index_names.add(index_name)
        return indexed

    def _stable_fallback_doc_id(self, raw_data: dict[str, Any]) -> str:
        source_payload = {
            "title": str(raw_data.get("title") or raw_data.get("display_name") or ""),
            "publication_year": raw_data.get("publication_year"),
            "source_index": self.target.source_index,
        }
        digest = hashlib.sha256(
            json.dumps(source_payload, sort_keys=True, ensure_ascii=True).encode("utf-8")
        ).hexdigest()
        return f"doc_{digest[:20]}"


__all__ = ["SilverETLPipeline", "empty_pipeline_result"]
