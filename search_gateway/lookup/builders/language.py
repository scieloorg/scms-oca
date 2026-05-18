from typing import Any

from search_gateway.lookup.base import LookupBuilder


class DocumentLanguageLookupBuilder(LookupBuilder):
    key = "document_language"
    default_index_name = "silver_lookup_document_language"
    source_fields = ["language"]

    def collect(self, source: dict[str, Any], max_items: int | None = None) -> None:
        seen_values: set[str] = set()

        for value in self.iter_clean_values(source.get("language")):
            self.add_entry(value, value, seen_values, max_items)
