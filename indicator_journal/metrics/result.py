from typing import Any, Dict


class JournalMetricResultBuilder:
    def __init__(self, data_source: Any):
        self.data_source = data_source

    def get_nested_value(self, data: Dict[str, Any], path: str, default: Any = None) -> Any:
        if not path:
            return default
        current = data
        for part in path.split("."):
            if not isinstance(current, dict):
                return default
            current = current.get(part)
        return default if current is None else current

    def parse_hit(self, hit: Dict[str, Any]) -> Dict[str, Any]:
        source = hit.get("_source") or {}
        parsed = {}
        for field in self.data_source.get_ordered_fields():
            parsed[field.field_name] = self.get_nested_value(source, field.index_field_name)

        parsed["id"] = hit.get("_id")
        parsed["journal_id"] = parsed.get("journal_id") or parsed.get("id")
        parsed["issn"] = parsed.get("journal_issn") or ""
        parsed["title"] = parsed.get("journal_title") or "Unknown"
        parsed["country"] = parsed.get("country") or ""
        parsed["publisher_name"] = parsed.get("publisher_name") or ""
        return parsed

    def resolve_journal_identity(self, hit_source: Dict[str, Any], issn: str) -> Dict[str, Any]:
        def _field(name):
            return self.get_nested_value(hit_source, self.data_source.get_index_field_name(name))

        return {
            "journal_id": _field("journal_id"),
            "journal_title": _field("journal_title"),
            "journal_issn": _field("journal_issn") or issn,
            "country": _field("country"),
            "publisher_name": _field("publisher_name"),
        }

    def normalize_global_source(
        self,
        source: Dict[str, Any],
        global_ds: Any,
        journal_issn: str = None,
        journal_identity: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        if not source:
            return {}

        journal_identity = journal_identity or {}

        def _field(name):
            return self.get_nested_value(source, global_ds.get_index_field_name(name))

        result = {
            field.field_name: _field(field.field_name)
            for field in global_ds.get_ordered_fields()
        }

        result["journal_id"] = result.get("journal_id") or journal_identity.get("journal_id")
        result["journal_title"] = result.get("journal_title") or journal_identity.get("journal_title")
        result["journal_issn"] = result.get("journal_issn") or journal_identity.get("journal_issn") or journal_issn
        result["country"] = result.get("country") or journal_identity.get("country")
        result["publisher_name"] = result.get("publisher_name") or journal_identity.get("publisher_name")

        return result
