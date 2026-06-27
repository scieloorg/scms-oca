import hashlib
import logging
from collections import Counter
from collections.abc import Iterable
from typing import Any

from django.conf import settings
from opensearchpy.helpers import scan, streaming_bulk

from search_gateway.option_normalization import clean_text, normalize_boolean, normalize_text
from search_gateway.opensearch import OpenSearchIndexClient

logger = logging.getLogger(__name__)


class LookupBuilder:
    key: str
    default_index_name: str
    source_fields: list[str] = []

    def __init__(self) -> None:
        self.entries: dict[str, dict[str, Any]] = {}
        self.counts: Counter[str] = Counter()

    @staticmethod
    def build_mapping(extra_properties: dict[str, Any] | None = None) -> dict[str, Any]:
        properties: dict[str, Any] = {
            "value": {"type": "keyword", "ignore_above": 512},
            "normalized_value": {"type": "keyword", "ignore_above": 512},
            "label": {"type": "keyword", "ignore_above": 512, "copy_to": "label_search"},
            "label_search": {
                "type": "search_as_you_type",
                "analyzer": "multilingual",
                "doc_values": False,
                "max_shingle_size": 3,
            },
            "size": {"type": "integer"},
        }

        if extra_properties:
            properties.update(extra_properties)

        return {
            "settings": {
                "index": {
                    "number_of_shards": getattr(settings, "SEARCH_GATEWAY_LOOKUP_NUMBER_OF_SHARDS", 1),
                    "number_of_replicas": getattr(settings, "SEARCH_GATEWAY_LOOKUP_NUMBER_OF_REPLICAS", 0),
                    "refresh_interval": "-1",
                },
                "analysis": {
                    "analyzer": {
                        "multilingual": {
                            "type": "custom",
                            "tokenizer": "standard",
                            "filter": ["lowercase", "asciifolding"],
                        },
                    },
                },
            },
            "mappings": {
                "dynamic": "strict",
                "properties": properties,
            },
        }

    @property
    def mapping(self) -> dict[str, Any]:
        return self.build_mapping()

    @staticmethod
    def iter_clean_values(value: Any) -> Iterable[str]:
        if isinstance(value, (list, tuple, set)):
            for item in value:
                cleaned = clean_text(item)
                if cleaned:
                    yield cleaned
            return

        cleaned = clean_text(value)
        if cleaned:
            yield cleaned

    @staticmethod
    def iter_objects(value: Any) -> Iterable[dict[str, Any]]:
        if isinstance(value, dict):
            yield value
            return

        if isinstance(value, (list, tuple, set)):
            for item in value:
                if isinstance(item, dict):
                    yield item

    @staticmethod
    def clean_boolean_value(value):
        normalized = normalize_boolean(value)
        if normalized is True:
            return "true"

        if normalized is False:
            return "false"

        return ""

    @classmethod
    def iter_clean_boolean_values(cls, value):
        if isinstance(value, (list, tuple, set)):
            for item in value:
                cleaned = cls.clean_boolean_value(item)
                if cleaned:
                    yield cleaned
            return

        cleaned = cls.clean_boolean_value(value)
        if cleaned:
            yield cleaned

    def collect_document_metadata(self, source):
        return {
            "document_types": set(self.iter_clean_values(source.get("type"))),
            "document_languages": set(self.iter_clean_values(source.get("language"))),
            "open_access_values": set(
                self.iter_clean_boolean_values(source.get("is_open_access"))
            ),
            "open_access_statuses": set(
                self.iter_clean_values(source.get("open_access_status"))
            ),
        }

    def count(self):
        return len(self.entries)

    @staticmethod
    def document_id(value: str) -> str:
        digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
        return f"lookup_{digest}"

    def add_entry(
        self,
        value: str,
        label: str,
        seen_values: set[str],
        max_items: int | None = None,
        **extra: Any,
    ) -> dict[str, Any] | None:
        value = clean_text(value)
        label = clean_text(label)

        if not value or not label:
            return None

        is_new_value = value not in self.entries
        if max_items is not None and is_new_value and len(self.entries) >= max_items:
            return None

        if is_new_value:
            entry = {
                "value": value,
                "label": label,
                "normalized_value": normalize_text(label),
            }
            self.entries[value] = entry
        else:
            entry = self.entries[value]

        for key, extra_value in extra.items():
            if isinstance(extra_value, set):
                entry.setdefault(key, set()).update(extra_value)
            elif extra_value not in (None, "") and not entry.get(key):
                entry[key] = extra_value

        if value not in seen_values:
            self.counts[value] += 1
            seen_values.add(value)

        return entry

    def collect(self, source: dict[str, Any], max_items: int | None = None) -> None:
        raise NotImplementedError

    def iter_actions(self, index_name: str) -> Iterable[dict[str, Any]]:
        for value in sorted(self.entries.keys()):
            entry = self.entries[value]
            yield {
                "_op_type": "index",
                "_index": index_name,
                "_id": self.document_id(value),
                "_source": {
                    "value": entry["value"],
                    "label": entry["label"],
                    "normalized_value": entry["normalized_value"],
                    "size": self.counts[value],
                },
            }


class LookupIndexBuildService:
    def __init__(
        self,
        client: Any,
        lookup_builders: dict[str, type[LookupBuilder]],
        source_index: str,
        batch_size: int,
        selected_lookups: list[str],
        max_docs: int | None = None,
        lookup_index_overrides: dict[str, str] | None = None,
        max_items: dict[str, int] | None = None,
        progress=None,
    ) -> None:
        self.client = client
        self.lookup_builders = lookup_builders
        self.source_index = source_index
        self.batch_size = batch_size
        self.selected_lookups = selected_lookups
        self.max_docs = max_docs
        self.lookup_index_overrides = lookup_index_overrides or {}
        self.max_items = max_items or {}
        self.progress = progress

    def resolve_index_names(self, builders: dict[str, LookupBuilder]) -> dict[str, str]:
        index_names = {
            lookup_key: self.lookup_index_overrides.get(
                lookup_key,
                builder.default_index_name,
            )
            for lookup_key, builder in builders.items()
        }

        seen: dict[str, str] = {}
        for lookup_key, index_name in index_names.items():
            existing_lookup_key = seen.get(index_name)
            if existing_lookup_key:
                raise ValueError(
                    f"Lookups '{existing_lookup_key}' and '{lookup_key}' target the same "
                    f"index '{index_name}'. Please use different index names."
                )

            seen[index_name] = lookup_key

        return index_names

    def validate_source(self) -> None:
        if not self.client.ping():
            raise ConnectionError("Could not connect to OpenSearch.")

        if not self.client.indices.exists(index=self.source_index):
            raise ValueError(f"Source index or alias '{self.source_index}' does not exist.")

    def validate_targets(self, index_names: dict[str, str]) -> None:
        for lookup_key, index_name in index_names.items():
            if self.client.indices.exists(index=index_name):
                raise ValueError(
                    f"Target lookup index '{index_name}' already exists for lookup "
                    f"'{lookup_key}'. Use --lookup-index {lookup_key}=<new_index> "
                    "or delete the existing index first."
                )

    def collect(self, builders: dict[str, LookupBuilder]) -> int:
        source_fields = sorted(
            {field for builder in builders.values() for field in builder.source_fields}
        )
        query = {"_source": source_fields, "query": {"match_all": {}}}

        processed = 0
        if self.progress:
            self.progress(f"Scanning source index '{self.source_index}'...")

        for hit in scan(self.client, index=self.source_index, query=query, size=self.batch_size):
            source = hit.get("_source", {})
            processed += 1

            for lookup_key, builder in builders.items():
                builder.collect(source, self.max_items.get(lookup_key))

            if self.progress and processed % 10000 == 0:
                self.progress(f"Processed {processed:,} source documents...")

            if self.max_docs is not None and processed >= self.max_docs:
                break

        if self.progress:
            self.progress(f"Finished scanning {processed:,} documents.")

        return processed

    def _truncate(self, value: Any, limit: int = 160) -> str | None:
        if value is None:
            return None

        text = str(value)
        if len(text) <= limit:
            return text

        return f"{text[:limit]}..."

    def _safe_bulk_error(self, item: Any) -> dict[str, Any]:
        if not isinstance(item, dict) or not item:
            return {"error": self._truncate(item)}

        action, info = next(iter(item.items()))
        if not isinstance(info, dict):
            return {"action": action, "error": self._truncate(info)}

        data = info.get("data") if isinstance(info.get("data"), dict) else {}
        return {
            "action": action,
            "_index": info.get("_index"),
            "_id": self._truncate(info.get("_id")),
            "status": info.get("status"),
            "error": self._truncate(info.get("error")),
            "value": self._truncate(data.get("value")),
            "label": self._truncate(data.get("label")),
        }

    def record_bulk_errors(
        self,
        lookup_key: str,
        index_name: str,
        success_count: int,
        error_count: int,
        expected_count: int,
        sample_errors: list[Any],
    ) -> None:
        if not error_count:
            return

        message = (
            f"Lookup '{lookup_key}' indexed partially in '{index_name}': "
            f"{success_count:,} succeeded and {error_count:,} failed."
        )
        context = {
            "source_index": self.source_index,
            "lookup_key": lookup_key,
            "index_name": index_name,
            "success_count": success_count,
            "error_count": error_count,
            "expected_count": expected_count,
            "sample_errors": sample_errors,
        }

        try:
            OpenSearchIndexClient(client=self.client).index_error(
                component="search_gateway.lookup",
                operation="build_lookup_indices",
                message=message,
                error_type="BulkIndexPartialFailure",
                context=context,
            )
        except Exception:
            logger.exception("Failed to write lookup bulk error summary")

    def bulk_index(
        self,
        lookup_key: str,
        index_name: str,
        actions: Iterable[dict[str, Any]],
        expected_count: int,
    ) -> dict[str, int]:
        success = 0
        error_count = 0
        sample_errors = []

        if self.progress:
            self.progress(
                f"Starting bulk indexing {expected_count:,} lookup documents "
                f"in '{index_name}'..."
            )

        try:
            for ok, item in streaming_bulk(
                self.client,
                actions,
                chunk_size=self.batch_size,
                max_retries=3,
                raise_on_error=False,
                raise_on_exception=False,
            ):
                if ok:
                    success += 1
                    if self.progress and success % 5000 == 0:
                        self.progress(f"Indexed {success:,} lookup documents in '{index_name}'...")
                else:
                    error_count += 1
                    if len(sample_errors) < 5:
                        sample_errors.append(self._safe_bulk_error(item))

        except Exception as exc:
            raise ValueError(
                f"Fatal bulk indexing failure for lookup '{lookup_key}' in '{index_name}' "
                f"after indexing {success:,} of {expected_count:,} lookup documents. "
                f"Error: {exc}"
            ) from exc

        self.record_bulk_errors(
            lookup_key=lookup_key,
            index_name=index_name,
            success_count=success,
            error_count=error_count,
            expected_count=expected_count,
            sample_errors=sample_errors,
        )

        if error_count and self.progress:
            self.progress(
                f"Finished indexing '{index_name}' with {success:,} successes "
                f"and {error_count:,} errors."
            )

        if self.progress and not error_count:
            self.progress(f"Finished indexing {success:,} documents in '{index_name}'.")

        self.client.indices.refresh(index=index_name)
        count_response = self.client.count(index=index_name)

        if hasattr(count_response, "get"):
            indexed_total = count_response.get("count")

        elif hasattr(count_response, "body") and hasattr(count_response.body, "get"):
            indexed_total = count_response.body.get("count")

        else:
            indexed_total = None

        if indexed_total != success:
            raise ValueError(
                f"Index '{index_name}' count mismatch after refresh: bulk reported "
                f"{success:,} successful documents, but OpenSearch count returned "
                f"{indexed_total!r}."
            )

        if expected_count != success + error_count:
            raise ValueError(
                f"Index '{index_name}' expected {expected_count:,} lookup documents, "
                f"but bulk reported {success:,} successful and {error_count:,} failed documents."
            )

        if self.progress:
            self.progress(f"Verified {indexed_total:,} documents in '{index_name}'.")

        return {"indexed": success, "errors": error_count}

    def create_indices(self, builders: dict[str, LookupBuilder], index_names: dict[str, str]) -> None:
        for lookup_key, builder in builders.items():
            index_name = index_names[lookup_key]
            self.client.indices.create(index=index_name, body=builder.mapping)

    def run(self) -> dict[str, Any]:
        builders: dict[str, LookupBuilder] = {
            key: self.lookup_builders[key]() for key in self.selected_lookups
        }
        index_names = self.resolve_index_names(builders)

        self.validate_source()
        self.validate_targets(index_names)

        processed_docs = self.collect(builders)
        indexed_counts: dict[str, Any] = {"_processed_docs": processed_docs}
        error_counts: dict[str, int] = {}

        self.validate_targets(index_names)
        self.create_indices(builders, index_names)

        for lookup_key, builder in builders.items():
            index_name = index_names[lookup_key]
            if self.progress:
                self.progress(
                    f"Collected {builder.count():,} values for lookup '{lookup_key}' "
                    f"from {processed_docs:,} documents."
                )

            bulk_result = self.bulk_index(
                lookup_key,
                index_name,
                builder.iter_actions(index_name),
                builder.count(),
            )

            indexed_counts[lookup_key] = bulk_result["indexed"]
            if bulk_result["errors"]:
                error_counts[lookup_key] = bulk_result["errors"]

        if error_counts:
            indexed_counts["_errors"] = error_counts

        return indexed_counts
