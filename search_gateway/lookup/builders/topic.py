from collections.abc import Iterable
from typing import Any

from search_gateway.lookup.base import LookupBuilder, clean_text


class TopicLookupBuilder(LookupBuilder):
    key = "topic"
    default_index_name = "lookup_topic"
    source_fields = [
        "topics.name",
        "topics.domain",
        "topics.field",
        "topics.subfield",
        "primary_topic_name",
        "primary_topic_domain",
        "primary_topic_field",
        "primary_topic_subfield",
        "topic_domains",
        "topic_fields",
        "topic_subfields",
    ]
    @property
    def mapping(self) -> dict[str, Any]:
        return self.build_mapping(
            {
                "topic_levels": {"type": "keyword"},
                "parent_domains": {"type": "keyword"},
                "parent_fields": {"type": "keyword"},
                "parent_subfields": {"type": "keyword"},
            }
        )

    def collect(self, source: dict[str, Any], max_items: int | None = None) -> None:
        seen_values: set[str] = set()

        for topic in self.iter_objects(source.get("topics")):
            name = clean_text(topic.get("name"))
            domain = clean_text(topic.get("domain"))
            field = clean_text(topic.get("field"))
            subfield = clean_text(topic.get("subfield"))

            self.collect_level(domain, "domain", seen_values, max_items)
            self.collect_level(field, "field", seen_values, max_items, parent_domain=domain or None)
            self.collect_level(
                subfield,
                "subfield",
                seen_values,
                max_items,
                parent_domain=domain or None,
                parent_field=field or None,
            )
            self.collect_level(
                name,
                "topic",
                seen_values,
                max_items,
                parent_domain=domain or None,
                parent_field=field or None,
                parent_subfield=subfield or None,
            )

        self.collect_level(
            source.get("primary_topic_name"),
            "topic",
            seen_values,
            max_items,
            parent_domain=clean_text(source.get("primary_topic_domain")) or None,
            parent_field=clean_text(source.get("primary_topic_field")) or None,
            parent_subfield=clean_text(source.get("primary_topic_subfield")) or None,
        )
        self.collect_level(source.get("topic_domains"), "domain", seen_values, max_items)
        self.collect_level(source.get("topic_fields"), "field", seen_values, max_items)
        self.collect_level(source.get("topic_subfields"), "subfield", seen_values, max_items)

    def collect_level(
        self,
        values: Any,
        level: str,
        seen_values: set[str],
        max_items: int | None,
        parent_domain: str | None = None,
        parent_field: str | None = None,
        parent_subfield: str | None = None,
    ) -> None:
        for value in self.iter_clean_values(values):
            entry = self.add_entry(value, value, seen_values, max_items)
            if not entry:
                continue

            entry.setdefault("topic_levels", set()).add(level)
            if parent_domain:
                entry.setdefault("parent_domains", set()).add(parent_domain)
            if parent_field:
                entry.setdefault("parent_fields", set()).add(parent_field)
            if parent_subfield:
                entry.setdefault("parent_subfields", set()).add(parent_subfield)

    def iter_actions(self, index_name: str) -> Iterable[dict[str, Any]]:
        for action in super().iter_actions(index_name):
            entry = self.entries[action["_source"]["value"]]
            action["_source"].update(
                {
                    "topic_levels": sorted(entry.get("topic_levels", set())),
                    "parent_domains": sorted(entry.get("parent_domains", set())),
                    "parent_fields": sorted(entry.get("parent_fields", set())),
                    "parent_subfields": sorted(entry.get("parent_subfields", set())),
                }
            )
            yield action
