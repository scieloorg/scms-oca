from collections.abc import Iterable
from typing import Any

from search_gateway.lookup.base import LookupBuilder, clean_text


class SourceLookupBuilder(LookupBuilder):
    key = "source"
    default_index_name = "lookup_source"
    source_fields = [
        "sources.title",
        "sources.id",
        "sources.type",
        "sources.issn_l",
        "publishers.id",
    ]
    @property
    def mapping(self) -> dict[str, Any]:
        return self.build_mapping(
            {
                "source_id": {"type": "keyword"},
                "source_type": {"type": "keyword"},
                "source_issn_l": {"type": "keyword"},
                "publisher_ids": {"type": "keyword"},
            }
        )

    def collect(self, source: dict[str, Any], max_items: int | None = None) -> None:
        seen_values: set[str] = set()
        publisher_ids = set()

        for publisher in self.iter_objects(source.get("publishers")):
            publisher_ids.update(self.iter_clean_values(publisher.get("id")))

        for src in self.iter_objects(source.get("sources")):
            source_id = clean_text(src.get("id"))
            if not source_id:
                continue

            entry = self.add_entry(
                source_id,
                clean_text(src.get("title")) or source_id,
                seen_values,
                max_items,
                source_id=source_id,
                source_type=clean_text(src.get("type")),
                source_issn_l=clean_text(src.get("issn_l")),
            )

            if entry:
                entry.setdefault("publisher_ids", set()).update(publisher_ids)

    def iter_actions(self, index_name: str) -> Iterable[dict[str, Any]]:
        for action in super().iter_actions(index_name):
            entry = self.entries[action["_source"]["value"]]
            action["_source"].update(
                {
                    "source_id": entry.get("source_id", ""),
                    "source_type": entry.get("source_type", ""),
                    "source_issn_l": entry.get("source_issn_l", ""),
                    "publisher_ids": sorted(entry.get("publisher_ids", set())),
                }
            )
            yield action
