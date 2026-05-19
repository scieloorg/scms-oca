from collections.abc import Iterable
from typing import Any

from search_gateway.lookup.base import LookupBuilder, clean_text


class FunderLookupBuilder(LookupBuilder):
    key = "funder"
    default_index_name = "silver_lookup_funder"
    source_fields = ["funders.name", "funders.id", "funders.ror"]
    @property
    def mapping(self) -> dict[str, Any]:
        return self.build_mapping(
            {
                "funder_id": {"type": "keyword"},
                "funder_ror": {"type": "keyword"},
            }
        )

    def collect(self, source: dict[str, Any], max_items: int | None = None) -> None:
        seen_values: set[str] = set()

        for funder in self.iter_objects(source.get("funders")):
            funder_id = clean_text(funder.get("id"))
            if not funder_id:
                continue

            self.add_entry(
                funder_id,
                clean_text(funder.get("name")),
                seen_values,
                max_items,
                funder_id=funder_id,
                funder_ror=clean_text(funder.get("ror")),
            )

    def iter_actions(self, index_name: str) -> Iterable[dict[str, Any]]:
        for action in super().iter_actions(index_name):
            entry = self.entries[action["_source"]["value"]]
            action["_source"].update(
                {
                    "funder_id": entry.get("funder_id", ""),
                    "funder_ror": entry.get("funder_ror", ""),
                }
            )
            yield action
