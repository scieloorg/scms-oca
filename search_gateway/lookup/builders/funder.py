from collections.abc import Iterable
from typing import Any

from search_gateway.lookup.base import LookupBuilder, clean_text


class FunderLookupBuilder(LookupBuilder):
    key = "funder"
    default_index_name = "silver_lookup_funder"
    source_fields = [
        "author_country_codes",
        "funders.name",
        "funders.id",
        "funders.ror",
        "institutions",
        "is_open_access",
        "language",
        "open_access_status",
        "sdg_names",
        "type",
    ]

    @property
    def mapping(self) -> dict[str, Any]:
        return self.build_mapping(
            {
                "funder_id": {"type": "keyword"},
                "funder_ror": {"type": "keyword"},
                "sdg_names": {"type": "keyword"},
                "country_codes": {"type": "keyword"},
                "institution_names": {"type": "keyword"},
                "document_types": {"type": "keyword"},
                "document_languages": {"type": "keyword"},
                "open_access_values": {"type": "keyword"},
                "open_access_statuses": {"type": "keyword"},
            }
        )

    def collect(self, source: dict[str, Any], max_items: int | None = None) -> None:
        seen_values: set[str] = set()
        sdg_names = set(self.iter_clean_values(source.get("sdg_names")))
        country_codes = set(self.iter_clean_values(source.get("author_country_codes")))
        institution_names = set(self.iter_clean_values(source.get("institutions")))
        document_metadata = self.collect_document_metadata(source)

        for funder in self.iter_objects(source.get("funders")):
            funder_id = clean_text(funder.get("id"))
            if not funder_id:
                continue

            entry = self.add_entry(
                funder_id,
                clean_text(funder.get("name")),
                seen_values,
                max_items,
                funder_id=funder_id,
                funder_ror=clean_text(funder.get("ror")),
            )
            if entry:
                entry.setdefault("sdg_names", set()).update(sdg_names)
                entry.setdefault("country_codes", set()).update(country_codes)
                entry.setdefault("institution_names", set()).update(institution_names)
                for field_name, values in document_metadata.items():
                    entry.setdefault(field_name, set()).update(values)

    def iter_actions(self, index_name: str) -> Iterable[dict[str, Any]]:
        for action in super().iter_actions(index_name):
            entry = self.entries[action["_source"]["value"]]
            action["_source"].update(
                {
                    "funder_id": entry.get("funder_id", ""),
                    "funder_ror": entry.get("funder_ror", ""),
                    "sdg_names": sorted(entry.get("sdg_names", set())),
                    "country_codes": sorted(entry.get("country_codes", set())),
                    "institution_names": sorted(
                        entry.get("institution_names", set())
                    ),
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
