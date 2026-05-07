from dataclasses import dataclass
from fnmatch import fnmatch


@dataclass(frozen=True)
class PipelineTarget:
    document_type: str
    source_index: str
    silver_index_pattern: str

    def matches_source_index(self, source_index: str) -> bool:
        return fnmatch(source_index, self.source_index)

    def silver_index_name(self, publication_year: int | None) -> str:
        if "{year}" in self.silver_index_pattern:
            if publication_year is None:
                raise ValueError("publication_year is required for year-partitioned silver indices")
            return self.silver_index_pattern.format(year=publication_year)
        return self.silver_index_pattern


def normalize_document_type(value: str | None) -> str:
    if value in (None, ""):
        raise ValueError("document_type is required")
    return str(value).strip().lower().replace("_", "-")


__all__ = [
    "PipelineTarget",
    "normalize_document_type",
]
