from collections.abc import Iterable
from typing import Any

from django.conf import settings

from search_gateway.lookup.base import LookupBuilder, clean_text


class SourceLookupBuilder(LookupBuilder):
    key = "source"
    default_index_name = "silver_lookup_source"
    source_fields = [
        "indexed_in",
        "is_open_access",
        "language",
        "oca_data.scielo.collection",
        "oca_data.scielo.source.country_code",
        "oca_data.scielo.source.indexed_in",
        "open_access_status",
        "source.title",
        "source.ids.openalex",
        "source.type",
        "source.issn_l",
        "type",
        "publishers.id",
        "publishers.name",
    ]

    @property
    def mapping(self) -> dict[str, Any]:
        return self.build_mapping(
            {
                "source_id": {"type": "keyword"},
                "source_type": {"type": "keyword"},
                "source_issn_l": {"type": "keyword"},
                "publisher_ids": {"type": "keyword"},
                "publisher_names": {"type": "keyword"},
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
        seen_values: set[str] = set()
        publisher_ids = set()
        publisher_names = set()
        allowed_source_types = self.allowed_source_types()
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

        for publisher in self.iter_objects(source.get("publishers")):
            publisher_ids.update(self.iter_clean_values(publisher.get("id")))
            publisher_names.update(self.iter_clean_values(publisher.get("name")))

        for src in self.iter_objects(source.get("source")):
            source_type = clean_text(src.get("type"))
            if source_type.lower() not in allowed_source_types:
                continue

            title = clean_text(src.get("title"))
            if not title:
                continue

            source_id = clean_text((src.get("ids") or {}).get("openalex"))
            entry = self.add_entry(
                value=title,
                label=title,
                seen_values=seen_values,
                max_items=max_items,
                source_id=source_id,
                source_type=source_type,
                source_issn_l=clean_text(src.get("issn_l")),
            )

            if entry:
                entry.setdefault("publisher_ids", set()).update(publisher_ids)
                entry.setdefault("publisher_names", set()).update(publisher_names)
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
                    "source_id": entry.get("source_id", ""),
                    "source_type": entry.get("source_type", ""),
                    "source_issn_l": entry.get("source_issn_l", ""),
                    "publisher_ids": sorted(entry.get("publisher_ids", set())),
                    "publisher_names": sorted(entry.get("publisher_names", set())),
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
