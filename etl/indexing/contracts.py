from dataclasses import asdict, dataclass, field
from typing import Any

__all__ = ["BronzeDocument", "OcaModel", "SilverDocument"]


@dataclass
class OcaModel:
    def to_dict(self) -> dict:
        return self._clean_dict(asdict(self))

    def _clean_dict(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {
                key: self._clean_dict(item)
                for key, item in value.items()
                if item is not None and item != [] and item != {}
            }
        if isinstance(value, list):
            return [self._clean_dict(item) for item in value if item is not None]
        return value

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)


@dataclass
class BronzeDocument(OcaModel):
    doc_id: str
    document_type: str
    source: str
    raw_data: dict = field(default_factory=dict)
    publication_year: int | None = None
    publication_date: str | None = None
    doi: str | None = None
    oca_data: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.doc_id or not isinstance(self.doc_id, str):
            raise ValueError("doc_id must be a non-empty string")
        if not self.document_type:
            raise ValueError("document_type must be provided")
        if self.publication_year is not None:
            if not isinstance(self.publication_year, int):
                raise TypeError("publication_year must be int")
            if not (1000 <= self.publication_year <= 2100):
                raise ValueError("publication_year must be between 1000 and 2100")


@dataclass
class SilverDocument(OcaModel):
    doc_id: str
    type: str
    publication_year: int | None = None
    publication_date: str | None = None
    language: str | list[str] | None = None
    title: str | None = None
    abstract: str | None = None
    description: str | None = None
    keywords: list = field(default_factory=list)
    subjects: list = field(default_factory=list)
    ids: dict = field(default_factory=dict)
    doi: str | None = None
    issn: str | None = None
    isbn: str | None = None
    openalex_id: str | None = None
    scielo_id: str | None = None
    source: dict = field(default_factory=dict)
    content_url: str | None = None
    is_open_access: bool | None = None
    open_access_status: str | None = None
    metrics: dict = field(default_factory=dict)
    citation_count: int | None = None
    oca_data: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.doc_id or not isinstance(self.doc_id, str):
            raise ValueError("doc_id must be a non-empty string")
        if not self.type:
            raise ValueError("type must be provided")
        if self.publication_year is not None:
            if not isinstance(self.publication_year, int):
                raise TypeError("publication_year must be int")
            if not (1000 <= self.publication_year <= 2100):
                raise ValueError("publication_year must be between 1000 and 2100")
        if self.oca_data and not isinstance(self.oca_data, dict):
            raise TypeError("oca_data must be a dict")

    def get_scope(self) -> list[str]:
        scope = self.oca_data.get("scope")
        if isinstance(scope, str):
            return [scope]
        if isinstance(scope, list):
            return [item for item in scope if isinstance(item, str)]
        return []

    def is_merged(self) -> bool:
        scope = set(self.get_scope())
        return "scielo" in scope and "openalex" in scope

    def to_index_dict(self) -> dict:
        data = {
            "doc_id": self.doc_id,
            "type": self.type,
            "publication_year": self.publication_year,
            "publication_date": self.publication_date,
            "language": self.language,
            "title": self.title,
            "abstract": self.abstract,
            "description": self.description,
            "keywords": self.keywords,
            "subjects": self.subjects,
            "ids": self._index_ids(),
            "source": self.source,
            "content_url": self.content_url,
            "is_open_access": self.is_open_access,
            "open_access_status": self.open_access_status,
            "metrics": self._index_metrics(),
            "oca_data": self._index_oca_data(),
        }
        return self._clean_dict(data)

    def _index_ids(self) -> dict:
        ids = dict(self.ids or {})
        for key, value in {
            "doi": self.doi,
            "issn": self.issn,
            "isbn": self.isbn,
            "openalex": self.openalex_id,
            "scielo": self.scielo_id,
        }.items():
            if value and key not in ids:
                ids[key] = value
        return ids

    def _index_metrics(self) -> dict:
        metrics = dict(self.metrics or {})
        if self.citation_count is not None:
            received = dict(metrics.get("received_citations") or {})
            received.setdefault("total", self.citation_count)
            metrics["received_citations"] = received
        return metrics

    def _index_oca_data(self) -> dict:
        data = dict(self.oca_data or {})
        if "scope" in data and isinstance(data["scope"], str):
            data["scope"] = [data["scope"]]
        return data
