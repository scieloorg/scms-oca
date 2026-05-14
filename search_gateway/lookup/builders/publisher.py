from collections.abc import Iterable
from typing import Any

from search_gateway.lookup.base import LookupBuilder, clean_text


class PublisherLookupBuilder(LookupBuilder):
    key = "publisher"
    default_index_name = "lookup_publisher"
    source_fields = ["sources.type", "publishers.name", "publishers.id"]
    @property
    def mapping(self) -> dict[str, Any]:
        return self.build_mapping({"publisher_id": {"type": "keyword"}})

    def collect(self, source: dict[str, Any], max_items: int | None = None) -> None:
        if not any(
            clean_text(src.get("type")).lower() == "journal"
            for src in self.iter_objects(source.get("sources"))
        ):
            return

        seen_values: set[str] = set()

        for publisher in self.iter_objects(source.get("publishers")):
            self.add_entry(
                clean_text(publisher.get("name")),
                clean_text(publisher.get("name")),
                seen_values,
                max_items,
                publisher_id=clean_text(publisher.get("id")),
            )

    def iter_actions(self, index_name: str) -> Iterable[dict[str, Any]]:
        for action in super().iter_actions(index_name):
            entry = self.entries[action["_source"]["value"]]
            action["_source"].update({"publisher_id": entry.get("publisher_id", "")})
            yield action
