from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from django.conf import settings
from opensearchpy.helpers import scan, streaming_bulk

from search_gateway.option_normalization import clean_text, normalize_text


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
                    "number_of_shards": getattr(settings, "SEARCH_GATEWAY_LOOKUP_NUMBER_OF_SHARDS", 5),
                    "number_of_replicas": getattr(settings, "SEARCH_GATEWAY_LOOKUP_NUMBER_OF_REPLICAS", 0),
                    "refresh_interval": "-1",
                },
                "analysis": {
                    "analyzer": {
                        "multilingual": {
                            "type": "custom",
                            "tokenizer": "standard",
                            "filter": ["lowercase"],
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

    def count(self) -> int:
        return len(self.entries)

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
                "_id": value,
                "_source": {
                    "value": entry["value"],
                    "label": entry["label"],
                    "normalized_value": entry["normalized_value"],
                    "size": self.counts[value],
                },
            }


@dataclass
class BuildConfig:
    source_index: str
    batch_size: int
    max_docs: int | None
    selected_lookups: list[str]
    lookup_index_overrides: dict[str, str]
    max_items: dict[str, int]


def build_lookup_indices(
    client: Any,
    config: BuildConfig,
    lookup_builders: dict[str, type[LookupBuilder]],
    *,
    progress=None,
) -> dict[str, int]:

    def _resolve_index_names(builders):
        index_names = {
            lookup_key: config.lookup_index_overrides.get(
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

    def _validate_target_indices(index_names):
        for lookup_key, index_name in index_names.items():
            if client.indices.exists(index=index_name):
                raise ValueError(
                    f"Target lookup index '{index_name}' already exists for lookup "
                    f"'{lookup_key}'. Use --lookup-index {lookup_key}=<new_index> "
                    "or delete the existing index first."
                )

    def _collect(builders):
        source_fields = sorted(
            {field for builder in builders.values() for field in builder.source_fields}
        )
        query = {"_source": source_fields, "query": {"match_all": {}}}
        processed = 0
        if progress:
            progress(f"Scanning source index '{config.source_index}'...")

        for hit in scan(client, index=config.source_index, query=query, size=config.batch_size):
            source = hit.get("_source", {})
            processed += 1
            for lookup_key, builder in builders.items():
                builder.collect(source, config.max_items.get(lookup_key))
            if progress and processed % 10000 == 0:
                progress(f"Processed {processed:,} source documents...")
            if config.max_docs is not None and processed >= config.max_docs:
                break

        if progress:
            progress(f"Finished scanning {processed:,} documents.")

        return processed

    def _bulk_index(index_name, actions):
        success = 0
        for ok, _ in streaming_bulk(
            client, actions, chunk_size=config.batch_size, max_retries=3, raise_on_error=True
        ):
            if ok:
                success += 1
                if progress and success % 10000 == 0:
                    progress(f"Indexed {success:,} lookup documents in '{index_name}'...")
        client.indices.refresh(index=index_name)
        return success

    builders: dict[str, LookupBuilder] = {
        key: lookup_builders[key]() for key in config.selected_lookups
    }

    if not client.ping():
        raise ConnectionError("Could not connect to OpenSearch.")
    if not client.indices.exists(index=config.source_index):
        raise ValueError(f"Source index or alias '{config.source_index}' does not exist.")

    for lookup_key, builder in builders.items():
        index_name = _index_name(lookup_key, builder)
        _ensure_index(index_name, builder.mapping)

    processed_docs = _collect(builders)
    indexed_counts: dict[str, int] = {"_processed_docs": processed_docs}

    for lookup_key, builder in builders.items():
        index_name = _index_name(lookup_key, builder)
        if progress:
            progress(
                f"Collected {builder.count():,} values for lookup '{lookup_key}' "
                f"from {processed_docs:,} documents."
            )
        indexed_counts[lookup_key] = _bulk_index(
            index_name, builder.iter_actions(index_name)
        )

    return indexed_counts
