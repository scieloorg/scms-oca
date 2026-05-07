from etl.extractors import (
    extract_doi,
    extract_source,
    first_value,
    normalize_identifiers,
    rebuild_abstract_from_inverted_index,
)
from etl.indexing.contracts import BronzeDocument, SilverDocument
from etl.normalizers import (
    int_or_none,
    normalize_keywords,
    normalize_text,
    stz_country_code,
    stz_language,
)


class DefaultStandardizer:
    """Default source-agnostic transformation from bronze payload to silver."""

    def run(self, bronze_doc: BronzeDocument) -> SilverDocument:
        raw_data = bronze_doc.raw_data or {}
        identifiers = normalize_identifiers({"doi": bronze_doc.doi, **raw_data})
        title = normalize_text(raw_data.get("title") or raw_data.get("display_name"))
        abstract = self._extract_abstract(raw_data)
        source = extract_source(raw_data)
        languages = self._extract_languages(raw_data)

        return SilverDocument(
            doc_id=bronze_doc.doc_id,
            type=bronze_doc.document_type,
            publication_year=bronze_doc.publication_year or int_or_none(raw_data.get("publication_year")),
            publication_date=bronze_doc.publication_date or raw_data.get("publication_date"),
            language=languages or None,
            title=title,
            abstract=abstract,
            description=normalize_text(raw_data.get("description")),
            keywords=normalize_keywords(raw_data.get("keywords")),
            subjects=normalize_keywords(raw_data.get("subjects")),
            ids=identifiers,
            doi=identifiers.get("doi") or extract_doi(raw_data),
            issn=identifiers.get("issn"),
            isbn=identifiers.get("isbn"),
            openalex_id=identifiers.get("openalex_id"),
            scielo_id=identifiers.get("scielo_id"),
            source=self._index_source(source, raw_data),
            content_url=self._extract_content_url(raw_data),
            is_open_access=self._extract_is_open_access(raw_data),
            open_access_status=self._extract_open_access_status(raw_data),
            metrics=self._extract_metrics(raw_data),
            citation_count=int_or_none(raw_data.get("cited_by_count") or raw_data.get("citation_count")),
            oca_data=self._build_oca_data(bronze_doc),
        )

    def _extract_abstract(self, raw_data: dict) -> str | None:
        if abstract := raw_data.get("abstract_text") or raw_data.get("abstract"):
            return normalize_text(abstract)
        if inverted_index := raw_data.get("abstract_inverted_index"):
            return rebuild_abstract_from_inverted_index(inverted_index)
        return None

    def _extract_languages(self, raw_data: dict) -> list[str]:
        raw_languages = raw_data.get("languages") or raw_data.get("language") or []
        if isinstance(raw_languages, str):
            raw_languages = [raw_languages]
        return sorted(
            {
                normalized
                for language in raw_languages
                if (normalized := stz_language(language))
            }
        )

    def _index_source(self, source: dict, raw_data: dict) -> dict:
        indexed_source = {
            "id": source.get("id"),
            "title": source.get("title") or source.get("display_name") or raw_data.get("journal_title"),
            "type": source.get("type") or raw_data.get("primary_source_type"),
            "issns": source.get("issns") or source.get("issn"),
        }
        return {key: value for key, value in indexed_source.items() if value not in (None, [], {})}

    def _extract_content_url(self, raw_data: dict):
        return first_value(
            raw_data.get("content_url")
            or (raw_data.get("open_access") or {}).get("oa_url")
            or (raw_data.get("primary_location") or {}).get("pdf_url")
            or (raw_data.get("primary_location") or {}).get("landing_page_url")
        )

    def _extract_is_open_access(self, raw_data: dict):
        if "is_open_access" in raw_data:
            return raw_data["is_open_access"]
        return (raw_data.get("open_access") or {}).get("is_oa")

    def _extract_open_access_status(self, raw_data: dict):
        return raw_data.get("open_access_status") or (raw_data.get("open_access") or {}).get("oa_status")

    def _extract_metrics(self, raw_data: dict) -> dict:
        citation_total = int_or_none(raw_data.get("cited_by_count") or raw_data.get("citation_count"))
        if citation_total is None:
            return {}
        return {"received_citations": {"total": citation_total}}

    def _build_oca_data(self, bronze_doc: BronzeDocument) -> dict:
        oca_data = dict(bronze_doc.oca_data or {})
        scope = oca_data.get("scope") or [bronze_doc.source]
        oca_data["scope"] = scope if isinstance(scope, list) else [scope]
        oca_data.setdefault(
            bronze_doc.source,
            {
                "ids": [bronze_doc.doc_id],
                "type": bronze_doc.document_type,
                "source": {
                    "country_code": stz_country_code(bronze_doc.raw_data.get("country_code")),
                    "indexed_in": bronze_doc.raw_data.get("indexed_in"),
                },
            },
        )
        return oca_data
