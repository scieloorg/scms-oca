from collections.abc import Iterable
from typing import Any

from django.conf import settings

from search_gateway.lookup.base import LookupBuilder, clean_text


class PublisherLookupBuilder(LookupBuilder):
    key = "publisher"
    default_index_name = "silver_lookup_publisher"
    source_fields = [
        "indexed_in",
        "is_open_access",
        "language",
        "oca_data.scielo.collection",
        "oca_data.scielo.source.country_code",
        "oca_data.scielo.source.indexed_in",
        "open_access_status",
        "source.title",
        "source.type",
        "type",
        "publishers.name",
        "publishers.id",
    ]

    @property
    def mapping(self) -> dict[str, Any]:
        return self.build_mapping(
            {
                "publisher_id": {"type": "keyword"},
                "source_names": {"type": "keyword"},
                "source_types": {"type": "keyword"},
                "source_country_codes": {"type": "keyword"},
                "indexed_in": {"type": "keyword"},
                "source_scielo_indexed_in": {"type": "keyword"},
                "collections": {"type": "keyword"},
                "document_types": {"type": "keyword"},
                "document_languages": {"type": "keyword"},
                "open_access_values": {"type": "keyword"},
                "open_access_statuses": {"type": "keyword"},
            }
        )

    @classmethod
    def allowed_source_types(cls):
        allowed_types = set()

        for source_type in settings.SEARCH_GATEWAY_LOOKUP_SOURCE_TYPES:
            cleaned = clean_text(source_type)
            if cleaned:
                allowed_types.add(cleaned.lower())

        return allowed_types

    def collect(self, source: dict[str, Any], max_items: int | None = None) -> None:
        allowed_source_types = self.allowed_source_types()
        source_names = set()
        source_types = set()
        oca_data = source.get("oca_data") or {}
        scielo = oca_data.get("scielo") or {}
        scielo_source = scielo.get("source") or {}
        source_country_codes = set(
            self.iter_clean_values(scielo_source.get("country_code"))
        )
        indexed_in = set(self.iter_clean_values(source.get("indexed_in")))
        source_scielo_indexed_in = set(
            self.iter_clean_values(scielo_source.get("indexed_in"))
        )
        collections = set(self.iter_clean_values(scielo.get("collection")))
        document_metadata = self.collect_document_metadata(source)

        for src in self.iter_objects(source.get("source")):
            source_type = clean_text(src.get("type"))
            if source_type.lower() not in allowed_source_types:
                continue
            source_types.add(source_type)

            title = clean_text(src.get("title"))
            if title:
                source_names.add(title)

        if not source_types:
            return

        seen_values: set[str] = set()

        for publisher in self.iter_objects(source.get("publishers")):
            entry = self.add_entry(
                clean_text(publisher.get("name")),
                clean_text(publisher.get("name")),
                seen_values,
                max_items,
                publisher_id=clean_text(publisher.get("id")),
            )
            if entry:
                entry.setdefault("source_names", set()).update(source_names)
                entry.setdefault("source_types", set()).update(source_types)
                entry.setdefault("source_country_codes", set()).update(
                    source_country_codes
                )
                entry.setdefault("indexed_in", set()).update(indexed_in)
                entry.setdefault("source_scielo_indexed_in", set()).update(
                    source_scielo_indexed_in
                )
                entry.setdefault("collections", set()).update(collections)
                for field_name, values in document_metadata.items():
                    entry.setdefault(field_name, set()).update(values)

    def iter_actions(self, index_name: str) -> Iterable[dict[str, Any]]:
        for action in super().iter_actions(index_name):
            entry = self.entries[action["_source"]["value"]]
            action["_source"].update(
                {
                    "publisher_id": entry.get("publisher_id", ""),
                    "source_names": sorted(entry.get("source_names", set())),
                    "source_types": sorted(entry.get("source_types", set())),
                    "source_country_codes": sorted(
                        entry.get("source_country_codes", set())
                    ),
                    "indexed_in": sorted(entry.get("indexed_in", set())),
                    "source_scielo_indexed_in": sorted(
                        entry.get("source_scielo_indexed_in", set())
                    ),
                    "collections": sorted(entry.get("collections", set())),
                    "document_types": sorted(entry.get("document_types", set())),
                    "document_languages": sorted(
                        entry.get("document_languages", set())
                    ),
                    "open_access_values": sorted(
                        entry.get("open_access_values", set())
                    ),
                    "open_access_statuses": sorted(
                        entry.get("open_access_statuses", set())
                    ),
                }
            )
            yield action
