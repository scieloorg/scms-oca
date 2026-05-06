from collections.abc import Iterable
from typing import Any

from search_gateway.lookup.base import LookupBuilder, clean_text


class InstitutionLookupBuilder(LookupBuilder):
    key = "institution"
    default_index_name = "lookup_institution"
    source_fields = [
        "authorships.institutions.name",
        "authorships.institutions.id",
        "authorships.institutions.ror",
        "authorships.institutions.type",
        "authorships.institutions.country_code",
    ]
    @property
    def mapping(self) -> dict[str, Any]:
        return self.build_mapping(
            {
                "institution_id": {"type": "keyword"},
                "institution_ror": {"type": "keyword"},
                "institution_types": {"type": "keyword"},
                "country_codes": {"type": "keyword"},
            }
        )

    def collect(self, source: dict[str, Any], max_items: int | None = None) -> None:
        seen_values: set[str] = set()

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

    def iter_actions(self, index_name: str) -> Iterable[dict[str, Any]]:
        for action in super().iter_actions(index_name):
            entry = self.entries[action["_id"]]
            action["_source"].update(
                {
                    "institution_id": entry.get("institution_id", ""),
                    "institution_ror": entry.get("institution_ror", ""),
                    "institution_types": sorted(entry.get("institution_types", set())),
                    "country_codes": sorted(entry.get("country_codes", set())),
                }
            )
            yield action
