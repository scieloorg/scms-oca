from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from typing import Any

from etl.transform.extractors import (
    extract_doi,
    extract_issns,
    extract_publication_year,
)
from etl.transform.normalizers import normalize_country_code, normalize_doi, normalize_openalex_id
from etl.transform.utils import dict_or_empty, int_or_none


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
class InputDocument(OcaModel, ABC):
    doc_id: str
    source: str
    document_type: str = ""
    raw_data: dict = field(default_factory=dict)
    publication_year: int | None = None
    publication_date: str | None = None
    doi: str | None = None

    def __post_init__(self):
        if not self.doc_id or not isinstance(self.doc_id, str):
            raise ValueError("doc_id must be a non-empty string")
        if not self.source:
            raise ValueError("source must be provided")

        self.raw_data = dict_or_empty(self.raw_data)

        if self.publication_year is not None:
            if not isinstance(self.publication_year, int):
                raise TypeError("publication_year must be int")
            if not (1000 <= self.publication_year <= 2100):
                raise ValueError("publication_year must be between 1000 and 2100")

    @property
    def source_payload(self) -> dict:
        return self.raw_data

    @property
    @abstractmethod
    def scope(self) -> list[str]:
        raise NotImplementedError

    def scielo_oca(self) -> dict | None:
        return None

    def openalex_oca(self) -> dict | None:
        return None

    def enrichment_payloads(self) -> list[dict]:
        return []


@dataclass
class BronzeInputDocument(InputDocument, ABC):
    source: str = field(default="scielo", init=False)

    @property
    @abstractmethod
    def bronze_source_kind(self) -> str:
        raise NotImplementedError

    @classmethod
    def from_raw(
        cls,
        raw_data: dict[str, Any],
        doc_type_fn,
        fallback_id_fn=None,
    ) -> "BronzeInputDocument":
        doc_id = cls._extract_doc_id(raw_data, fallback_id_fn)
        publication_year = extract_publication_year(raw_data)
        publication_date = raw_data.get("publication_date")
        doi = extract_doi(raw_data)

        instance = cls(
            doc_id=doc_id,
            raw_data=raw_data,
            publication_year=publication_year,
            publication_date=publication_date,
            doi=doi,
        )
        instance.document_type = doc_type_fn(raw_data)
        return instance

    @staticmethod
    def _extract_doc_id(raw_data: dict[str, Any], fallback_id_fn=None) -> str:
        ids = raw_data.get("ids") if isinstance(raw_data.get("ids"), dict) else {}

        doc_id = (
            raw_data.get("code")
            or raw_data.get("id")
            or raw_data.get("doc_id")
            or ids.get("scl_preprint_id")
            or ids.get("dataset_id")
        )
        if doc_id:
            return str(doc_id)
        if fallback_id_fn:
            return fallback_id_fn(raw_data)
        raise ValueError("Cannot determine doc_id from raw data")

    @property
    def scope(self) -> list[str]:
        return ["scielo"]

    def scielo_oca(self) -> dict:
        raw = self.raw_data
        ids = raw.get("ids") if isinstance(raw.get("ids"), dict) else {}

        pid_v2 = raw.get("pid_v2") or raw.get("code") or raw.get("dataset_id") or ids.get("scl_preprint_id") or ids.get("scl_book_id") or raw.get("id")
        pids = []
        if pid_v2:
            pids.append(pid_v2)

        collection = raw.get("collection")
        scielo_type = raw.get("type") or raw.get("document_type") or self.document_type

        issns = extract_issns(raw) or []

        return {
            "ids": pids,
            "collection": collection,
            "pid_v2": pid_v2,
            "type": scielo_type,
            "source": {
                "country_code": normalize_country_code(raw.get("country_code")),
                "indexed_in": raw.get("indexed_in"),
                "issns": issns,
            },
        }


@dataclass
class SciELOArticleInputDocument(BronzeInputDocument):
    document_type: str = field(default="article", init=False)

    @property
    def bronze_source_kind(self) -> str:
        return "article"


@dataclass
class SciELOPreprintInputDocument(BronzeInputDocument):
    document_type: str = field(default="preprint", init=False)

    @property
    def bronze_source_kind(self) -> str:
        return "preprint"


@dataclass
class SciELODatasetInputDocument(BronzeInputDocument):
    document_type: str = field(default="dataset", init=False)

    @property
    def bronze_source_kind(self) -> str:
        return "dataset"


@dataclass
class SciELOBookInputDocument(BronzeInputDocument):
    document_type: str = field(default="book", init=False)

    @property
    def bronze_source_kind(self) -> str:
        return "book"

    def parent_book_raw(self) -> dict:
        monograph = self.raw_data.get("monograph")
        if not isinstance(monograph, dict) or not monograph:
            return {}
        return {
            "id": monograph.get("id"),
            "title": monograph.get("title"),
            "publication_year": int_or_none(monograph.get("publication_year")),
            "language": monograph.get("language"),
            "ids": {
                key: monograph[key]
                for key in ("scl_book_id", "doi", "isbn", "eisbn")
                if monograph.get(key)
            },
            "publishers": monograph.get("publishers") or [],
            "authorships": monograph.get("authorships") or [],
        }


@dataclass
class RawOpenAlexInputDocument(InputDocument):
    source: str = field(default="openalex", init=False)

    @classmethod
    def from_raw(cls, raw_data: dict[str, Any]) -> "RawOpenAlexInputDocument":
        doc_id = raw_data.get("id")
        if not doc_id:
            raise ValueError("OpenAlex document must have an 'id' field")

        document_type = raw_data.get("type") or "article"
        publication_year = int_or_none(raw_data.get("publication_year") or raw_data.get("year"))
        publication_date = raw_data.get("publication_date")
        doi = extract_doi(raw_data)

        instance = cls(
            doc_id=doc_id,
            raw_data=raw_data,
            publication_year=publication_year,
            publication_date=publication_date,
            doi=doi,
        )
        instance.document_type = document_type
        return instance

    @property
    def scope(self) -> list[str]:
        return ["openalex"]

    def openalex_oca(self) -> dict:
        raw = self.raw_data
        ids = raw.get("ids") or {}
        openalex_ids = [value for value in (ids.get("openalex"), raw.get("id")) if value]

        content_url = (
            raw.get("content_url")
            or (raw.get("open_access") or {}).get("oa_url")
            or (raw.get("primary_location") or {}).get("pdf_url")
            or (raw.get("primary_location") or {}).get("landing_page_url")
        )

        is_open_access = raw.get("is_open_access")
        if is_open_access is None:
            is_open_access = (raw.get("open_access") or {}).get("is_oa")

        open_access_status = raw.get("open_access_status")
        if not open_access_status:
            open_access_status = (raw.get("open_access") or {}).get("oa_status")

        citation_total = raw.get("cited_by_count") or raw.get("citation_count")
        by_year = [
            {"year": item.get("year"), "total": item.get("cited_by_count") or item.get("total")}
            for item in raw.get("counts_by_year") or []
        ]
        metrics = {}
        if citation_total is not None or by_year:
            metrics["received_citations"] = {"total": citation_total, "by_year": by_year}

        return {
            "ids": list(dict.fromkeys(openalex_ids)),
            "versions": [
                {
                    "id": raw.get("id"),
                    "doi": raw.get("doi"),
                    "title": raw.get("title") or raw.get("display_name"),
                    "language": raw.get("language"),
                    "content_url": content_url,
                    "is_open_access": is_open_access,
                    "open_access_status": open_access_status,
                    "metrics": metrics,
                }
            ],
        }

    def enrichment_payloads(self) -> list[dict]:
        return [self.raw_data]


@dataclass
class SilverDocument(OcaModel):
    doc_id: str
    type: str
    publication_year: int | None = None
    publication_date: str | None = None
    language: str | list[str] | None = None
    title: str | None = None
    title_with_lang: list = field(default_factory=list)
    abstract: str | None = None
    abstract_with_lang: list = field(default_factory=list)
    description: str | None = None
    description_with_lang: list = field(default_factory=list)
    keywords: list = field(default_factory=list)
    keywords_with_lang: list = field(default_factory=list)
    subjects: list = field(default_factory=list)
    subjects_with_lang: list = field(default_factory=list)
    ids: dict = field(default_factory=dict)
    doi: str | None = None
    issn: str | None = None
    isbn: str | None = None
    mag: str | None = None
    pmcid: str | None = None
    pmid: str | None = None
    openalex_id: str | None = None
    scielo_id: str | None = None
    authorships: list = field(default_factory=list)
    author_country_codes: list = field(default_factory=list)
    source: dict = field(default_factory=dict)
    source_title: str | None = None
    source_issns: list = field(default_factory=list)
    source_type: str | None = None
    content_url: str | None = None
    content_url_with_lang: list = field(default_factory=list)
    is_open_access: bool | None = None
    open_access_status: str | None = None
    biblio: dict = field(default_factory=dict)
    parent_book: dict = field(default_factory=dict)
    volume: str | None = None
    issue: str | None = None
    first_page: str | None = None
    last_page: str | None = None
    metrics: dict = field(default_factory=dict)
    citation_count: int | None = None
    fwci: float | None = None
    funders: list = field(default_factory=list)
    awards: list = field(default_factory=list)
    publishers: list = field(default_factory=list)
    primary_topic_name: str = ""
    primary_topic_domain: str = ""
    primary_topic_field: str = ""
    primary_topic_subfield: str = ""
    primary_topic_score: float = 0.0
    apc: dict = field(default_factory=dict)
    authors_count: int = 0
    references_count: int = 0
    sustainable_development_goals: list = field(default_factory=list)
    referenced_works: list = field(default_factory=list)
    oca_data: dict = field(default_factory=dict)
    indexed_in: list = field(default_factory=list)

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
        return self._scope_values(self.oca_data.get("scope"))

    def is_merged(self) -> bool:
        scope = set(self.get_scope())
        return "scielo" in scope and "openalex" in scope

    def to_index_dict(self) -> dict:
        data = {
            "doc_id": self.doc_id,
            "oca_data": self._index_oca_data(),
            "ids": self._index_ids(),
            "type": self.type,
            "indexed_in": self.indexed_in,
            "language": self.language,
            "title": self.title,
            "title_with_lang": self._index_lang_items(self.title_with_lang, "title", aliases=("text",)),
            "abstract": self.abstract,
            "abstract_with_lang": self._index_lang_items(self.abstract_with_lang, "abstract", aliases=("text",)),
            "description": self.description,
            "description_with_lang": self._index_lang_items(self.description_with_lang, "description", aliases=("text",)),
            "keywords": self.keywords,
            "keywords_with_lang": self._index_lang_items(self.keywords_with_lang, "keywords", aliases=("keyword", "text")),
            "subjects": self.subjects,
            "subjects_with_lang": self._index_lang_items(self.subjects_with_lang, "subjects", aliases=("subject", "text")),
            "publication_date": self.publication_date,
            "publication_year": self.publication_year,
            "is_open_access": self.is_open_access,
            "open_access_status": self.open_access_status,
            "content_url": self.content_url,
            "content_url_with_lang": self._index_lang_items(self.content_url_with_lang, "content_url", aliases=("url", "text")),
            "biblio": self._index_biblio(),
            "parent_book": self._index_parent_book(),
            "referenced_works": self._index_referenced_works(),
            "authorships": self._index_authorships(),
            "author_country_codes": self.author_country_codes,
            "funders": self._index_funders(),
            "awards": self._index_awards(),
            "publishers": self._index_publishers(),
            "source": self._index_source(),
            "authors_count": self.authors_count,
            "references_count": self.references_count,
            "sustainable_development_goals": self._index_sdgs(),
            "sdg_names": self._index_sdg_names(),
            "metrics": self._index_metrics(),
        }
        data.update(self._index_primary_topic())
        data.update(self._index_apc())
        return self._clean_dict(data)

    def _index_ids(self) -> dict:
        ids = dict(self.ids or {})
        for key, value in {
            "doi": self.doi,
            "issn": self.issn,
            "isbn": self.isbn,
            "mag": self.mag,
            "pmcid": self.pmcid,
            "pmid": self.pmid,
            "openalex": self.openalex_id,
            "scielo": self.scielo_id,
        }.items():
            if value and key not in ids:
                ids[key] = value
        if ids.get("doi"):
            ids["doi"] = normalize_doi(ids["doi"])
            if not ids["doi"]:
                ids.pop("doi", None)
        ids["doi_with_lang"] = self._index_doi_lang_items(ids.get("doi_with_lang"))
        ids["openalex"] = self._index_openalex_id_values(ids.get("openalex"))
        ids["openalex_with_lang"] = self._index_openalex_lang_items(ids.get("openalex_with_lang"))
        if not ids["openalex"]:
            ids.pop("openalex", None)
        return self._only(
            ids,
            {"doi", "doi_with_lang", "issn", "isbn", "mag", "openalex", "openalex_with_lang", "pmcid", "pmid", "scielo"},
        )

    def _index_biblio(self) -> dict:
        biblio = dict(self.biblio or {})
        for key, value in {
            "volume": self.volume,
            "issue": self.issue,
            "first_page": self.first_page,
            "last_page": self.last_page,
        }.items():
            if value and key not in biblio:
                biblio[key] = value
        return self._only(biblio, {"volume", "issue", "first_page", "last_page"})

    def _index_parent_book(self) -> dict:
        parent = dict(self.parent_book or {})
        return self._only(
            {
                "id": parent.get("id"),
                "title": parent.get("title"),
                "publication_year": parent.get("publication_year"),
                "language": parent.get("language"),
                "ids": parent.get("ids") or {},
                "publishers": parent.get("publishers") or [],
                "authorships": parent.get("authorships") or [],
            },
            {"id", "title", "publication_year", "language", "ids", "publishers", "authorships"},
        )

    def _index_source(self) -> dict:
        source = dict(self.source or {})
        if self.source_title and "title" not in source:
            source["title"] = self.source_title
        if self.source_type and "type" not in source:
            source["type"] = self.source_type
        if self.source_issns and "issns" not in source:
            source["issns"] = self.source_issns
        return self._only(
            source,
            {"acronym", "title", "type", "is_open_access", "landing_page_url", "issns", "issn_l", "host_organization", "host_organization_name", "ids"},
        )

    def _index_metrics(self) -> dict:
        metrics = dict(self.metrics or {})
        if self.fwci is not None and "fwci" not in metrics:
            metrics["fwci"] = self.fwci
        if self.citation_count is not None:
            received = dict(metrics.get("received_citations") or {})
            received.setdefault("total", self.citation_count)
            metrics["received_citations"] = received
        return self._only(metrics, {"fwci", "received_citations"})

    def _index_authorships(self) -> list:
        indexed = []
        for authorship in self.authorships or []:
            if not isinstance(authorship, dict):
                continue
            author = authorship.get("author") or {}
            institutions = []
            for institution in authorship.get("institutions") or []:
                if isinstance(institution, dict):
                    institutions.append(
                        self._only(
                            {
                                "name": institution.get("name") or institution.get("display_name"),
                                "id": institution.get("id"),
                                "ror": institution.get("ror"),
                                "type": institution.get("type"),
                                "country_code": institution.get("country_code"),
                            },
                            {"name", "id", "ror", "type", "country_code"},
                        )
                    )
            indexed.append(
                self._only(
                    {
                        "author_position": authorship.get("author_position") or authorship.get("position"),
                        "name": authorship.get("name") or authorship.get("raw_author_name") or author.get("display_name"),
                        "id": authorship.get("id") or author.get("id"),
                        "orcid": authorship.get("orcid") or author.get("orcid"),
                        "institutions": institutions,
                    },
                    {"author_position", "name", "id", "orcid", "institutions"},
                )
            )
        return indexed

    def _index_funders(self) -> list:
        return [
            self._only(
                {
                    "name": item.get("name") or item.get("display_name"),
                    "id": item.get("id"),
                    "ror": item.get("ror"),
                    "country_code": item.get("country_code"),
                },
                {"name", "id", "ror", "country_code"},
            )
            for item in self.funders or []
            if isinstance(item, dict)
        ]

    def _index_awards(self) -> list:
        return [
            self._only(
                {
                    "funder_name": item.get("funder_name"),
                    "funder_id": item.get("funder_id"),
                    "award_id": item.get("award_id") or item.get("id"),
                },
                {"funder_name", "funder_id", "award_id"},
            )
            for item in self.awards or []
            if isinstance(item, dict)
        ]

    def _index_publishers(self) -> list:
        return [self._only(item, {"id", "name"}) for item in self.publishers or [] if isinstance(item, dict)]

    def _index_primary_topic(self) -> dict:
        if not self.primary_topic_name:
            return {}
        return {
            "primary_topic_name": self.primary_topic_name,
            "primary_topic_domain": self.primary_topic_domain,
            "primary_topic_field": self.primary_topic_field,
            "primary_topic_subfield": self.primary_topic_subfield,
            "primary_topic_score": self.primary_topic_score,
        }

    def _index_apc(self) -> dict:
        if not self.apc:
            return {}
        return {"apc": self._only(self.apc, {"apc_list", "apc_paid"})}

    def _index_sdgs(self) -> list:
        return [
            self._only(item, {"id", "display_name", "score"})
            for item in self.sustainable_development_goals or []
            if isinstance(item, dict)
        ]

    def _index_sdg_names(self) -> list:
        names = [
            item.get("display_name")
            for item in self.sustainable_development_goals or []
            if isinstance(item, dict) and item.get("display_name")
        ]
        return list(dict.fromkeys(names))

    def _index_referenced_works(self) -> dict:
        openalex_ids = []
        for work in self.referenced_works or []:
            if isinstance(work, str):
                openalex_ids.append(work)
                continue
            if isinstance(work, dict):
                ids = work.get("ids") or {}
                openalex_id = ids.get("openalex") or work.get("openalex")
                if openalex_id:
                    openalex_ids.append(openalex_id)
        if not openalex_ids:
            return {}
        return {"ids": {"openalex": openalex_ids}}

    def _index_lang_items(self, items: list, value_key: str, aliases: tuple[str, ...] = ()) -> list:
        indexed = []
        for item in items or []:
            if not isinstance(item, dict):
                continue
            value = item.get(value_key)
            if value is None:
                for alias in aliases:
                    value = item.get(alias)
                    if value is not None:
                        break
            indexed.append(
                self._only(
                    {"language": item.get("language") or item.get("lang"), value_key: value},
                    {"language", value_key},
                )
            )
        return indexed

    def _index_doi_lang_items(self, items: Any) -> list:
        indexed = []
        for item in items or []:
            if not isinstance(item, dict):
                continue
            value = item.get("doi") or item.get("id") or item.get("value")
            doi = normalize_doi(value)
            if doi:
                indexed.append(
                    self._only(
                        {"language": item.get("language") or item.get("lang"), "doi": doi},
                        {"language", "doi"},
                    )
                )
        return indexed

    def _index_openalex_lang_items(self, items: Any) -> list:
        indexed = []
        for item in items or []:
            if not isinstance(item, dict):
                continue
            value = item.get("openalex")
            if value is None:
                value = item.get("id") or item.get("value")
            openalex_id = normalize_openalex_id(value)
            if openalex_id:
                indexed.append(
                    self._only(
                        {"language": item.get("language") or item.get("lang"), "openalex": openalex_id},
                        {"language", "openalex"},
                    )
                )
        return indexed

    def _index_openalex_id_values(self, value: Any) -> Any:
        if value in (None, [], {}):
            return None
        values = value if isinstance(value, list) else [value]
        normalized = [
            openalex_id
            for item in values
            if (openalex_id := normalize_openalex_id(item))
        ]
        if not normalized:
            return None
        return normalized if isinstance(value, list) else normalized[0]

    def _index_oca_data(self) -> dict:
        raw = self.oca_data or {}
        allowed = {
            key: raw.get(key)
            for key in ("scope", "match_status", "match_strategy", "match_confidence", "merge_trace", "scielo", "openalex")
            if raw.get(key) not in (None, [], {})
        }
        if "scope" in allowed:
            allowed["scope"] = self._scope_values(allowed["scope"])

        trace = dict(allowed.get("merge_trace") or {})
        for key in ("scielo_id", "openalex_id"):
            if key in raw and key not in trace:
                trace[key] = raw[key]
        if trace:
            allowed["merge_trace"] = trace

        if self.scielo_id:
            scielo = dict(allowed.get("scielo") or {})
            scielo.setdefault("pid_v2", self.scielo_id)
            scielo.setdefault("ids", [self.scielo_id])
            allowed["scielo"] = scielo

        if self.openalex_id:
            openalex = dict(allowed.get("openalex") or {})
            existing_ids = self._openalex_ids(openalex.get("ids"))
            if self.openalex_id not in existing_ids:
                existing_ids.append(self.openalex_id)
            openalex["ids"] = existing_ids
            allowed["openalex"] = openalex

        if "scielo" in allowed:
            scielo = dict(allowed["scielo"])
            ids = self._list_values(scielo.get("ids") or scielo.get("pid_v2"))
            if ids:
                scielo["ids"] = ids
            scielo["source"] = self._only(scielo.get("source") or {}, {"country_code", "indexed_in"})
            allowed["scielo"] = self._only(scielo, {"ids", "collection", "pid_v2", "type", "source"})

        if "openalex" in allowed:
            openalex = dict(allowed["openalex"])
            openalex["ids"] = self._openalex_ids(openalex.get("ids"))
            openalex["versions"] = [
                self._only(
                    {
                        "id": version.get("id"),
                        "doi": version.get("doi"),
                        "title": version.get("title"),
                        "language": version.get("language"),
                        "content_url": version.get("content_url"),
                        "is_open_access": version.get("is_open_access"),
                        "open_access_status": version.get("open_access_status"),
                        "metrics": self._only(version.get("metrics") or {}, {"received_citations"}),
                    },
                    {"id", "doi", "title", "language", "content_url", "is_open_access", "open_access_status", "metrics"},
                )
                for version in openalex.get("versions") or []
                if isinstance(version, dict)
            ]
            allowed["openalex"] = self._only(openalex, {"ids", "versions"})

        return allowed

    def _scope_values(self, value: Any) -> list[str]:
        if value in (None, [], {}):
            return []
        if isinstance(value, str):
            return [value]
        if isinstance(value, (list, tuple, set)):
            return [item for item in value if isinstance(item, str) and item]
        return []

    def _list_values(self, value: Any) -> list:
        if value in (None, [], {}):
            return []
        values = value if isinstance(value, list) else [value]
        return list(dict.fromkeys(item for item in values if item))

    def _openalex_ids(self, value: Any) -> list:
        return [
            item
            for item in self._list_values(value)
            if isinstance(item, str) and "openalex.org/W" in item
        ]

    def _only(self, data: dict, keys: set[str]) -> dict:
        return {key: value for key, value in data.items() if key in keys}
