from collections.abc import Iterable
from typing import Any

from search_gateway.lookup.base import LookupBuilder, clean_text


class InstitutionLookupBuilder(LookupBuilder):
    key = "institution"
    default_index_name = "silver_lookup_institution"
    source_fields = [
        "authorships.institutions.name",
        "authorships.institutions.id",
        "authorships.institutions.ror",
        "authorships.institutions.type",
        "authorships.institutions.country_code",
        "funders.id",
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
                "institution_id": {"type": "keyword"},
                "institution_ror": {"type": "keyword"},
                "institution_types": {"type": "keyword"},
                "country_codes": {"type": "keyword"},
                "sdg_names": {"type": "keyword"},
                "funder_ids": {"type": "keyword"},
                "document_types": {"type": "keyword"},
                "document_languages": {"type": "keyword"},
                "open_access_values": {"type": "keyword"},
                "open_access_statuses": {"type": "keyword"},
            }
        )

    def collect(self, source: dict[str, Any], max_items: int | None = None) -> None:
        seen_values: set[str] = set()
        sdg_names = set(self.iter_clean_values(source.get("sdg_names")))
        funder_ids = set()
        document_metadata = self.collect_document_metadata(source)

        for funder in self.iter_objects(source.get("funders")):
            funder_ids.update(self.iter_clean_values(funder.get("id")))

        for authorship in self.iter_objects(source.get("authorships")):
            for institution in self.iter_objects(authorship.get("institutions")):
                entry = self.add_entry(
                    clean_text(institution.get("name")),
                    clean_text(institution.get("name")),
                    seen_values,
                    max_items,
                    institution_id=clean_text(institution.get("id")),
                    institution_ror=clean_text(institution.get("ror")),
                )
                if not entry:
                    continue

                entry.setdefault("institution_types", set()).update(
                    self.iter_clean_values(institution.get("type"))
                )
                entry.setdefault("country_codes", set()).update(
                    self.iter_clean_values(institution.get("country_code"))
                )
                entry.setdefault("sdg_names", set()).update(sdg_names)
                entry.setdefault("funder_ids", set()).update(funder_ids)
                for field_name, values in document_metadata.items():
                    entry.setdefault(field_name, set()).update(values)

    def iter_actions(self, index_name: str) -> Iterable[dict[str, Any]]:
        for action in super().iter_actions(index_name):
            entry = self.entries[action["_source"]["value"]]
            action["_source"].update(
                {
                    "institution_id": entry.get("institution_id", ""),
                    "institution_ror": entry.get("institution_ror", ""),
                    "institution_types": sorted(entry.get("institution_types", set())),
                    "country_codes": sorted(entry.get("country_codes", set())),
                    "sdg_names": sorted(entry.get("sdg_names", set())),
                    "funder_ids": sorted(entry.get("funder_ids", set())),
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
