import logging
from typing import Any

from etl.documents import (
    BronzeInputDocument,
    InputDocument,
    RawOpenAlexInputDocument,
    SciELOBookInputDocument,
    SilverDocument,
)
from etl.transform.extractors import (
    extract_abstract_from_inverted_index,
    extract_display_name,
    extract_identifiers,
)
from etl.transform.normalizers import (
    normalize_author_name,
    normalize_country_code,
    normalize_doi,
    normalize_document_type_for_etl,
    normalize_keywords,
    normalize_language,
    normalize_openalex_id,
    normalize_text,
)
from etl.transform.utils import as_list, first_value, int_or_none

logger = logging.getLogger(__name__)


def standardizer_for(input_doc: InputDocument) -> "BaseStandardizer":
    if isinstance(input_doc, SciELOBookInputDocument):
        return SciELOBookStandardizer()

    if isinstance(input_doc, BronzeInputDocument):
        return SciELOStandardizer()

    if isinstance(input_doc, RawOpenAlexInputDocument):
        return OpenAlexStandardizer()

    raise ValueError(f"Unknown input document type: {type(input_doc)}")


class BaseStandardizer:

    def run(self, input_doc: InputDocument) -> SilverDocument:
        data: dict[str, Any] = {}
        data["doc_id"] = input_doc.doc_id
        data["type"] = normalize_document_type_for_etl(input_doc.document_type)
        data["publication_year"] = input_doc.publication_year
        data["publication_date"] = input_doc.publication_date

        raw = input_doc.source_payload

        data.update(self._build_identifier_fields(input_doc))
        data.update(self._build_text_fields(raw))
        data.update(self._build_document_fields(input_doc))
        data["ids"] = self._build_ids_field(data, raw)
        data["oca_data"] = self._build_oca_data_field(input_doc)

        return SilverDocument(**data)

    def _build_identifier_fields(self, input_doc: InputDocument) -> dict[str, Any]:
        raw_doc = dict(input_doc.source_payload)
        if input_doc.doi:
            raw_doc["doi"] = input_doc.doi
        return extract_identifiers(raw_doc)

    def _build_ids_field(self, data: dict[str, Any], raw: dict[str, Any]) -> dict[str, Any]:
        ids = dict(raw.get("ids") or {})
        if doi_value := normalize_doi(ids.get("doi")):
            ids["doi"] = doi_value
        elif ids.get("doi"):
            ids.pop("doi", None)

        for src_key, dst_key in {
            "doi": "doi",
            "mag": "mag",
            "pmcid": "pmcid",
            "pmid": "pmid",
            "scielo_id": "scielo",
            "issn": "issn",
            "isbn": "isbn",
        }.items():
            if data.get(src_key):
                ids[dst_key] = data[src_key]

        if raw.get("doi_with_lang"):
            ids["doi_with_lang"] = self._normalize_doi_lang_items(raw["doi_with_lang"])
        elif ids.get("doi_with_lang"):
            ids["doi_with_lang"] = self._normalize_doi_lang_items(ids["doi_with_lang"])
        elif raw.get("doi") and raw.get("language"):
            if normalized := normalize_doi(raw["doi"]):
                ids["doi_with_lang"] = [{"language": raw["language"], "doi": normalized}]

        return ids

    def _normalize_doi_lang_items(self, items: Any) -> list:
        normalized = []
        for item in items or []:
            if not isinstance(item, dict):
                continue

            doi = normalize_doi(item.get("doi") or item.get("id") or item.get("value"))
            if doi:
                normalized.append({"language": item.get("language"), "doi": doi})

        return normalized

    def _build_text_fields(self, raw: dict[str, Any]) -> dict[str, Any]:
        data: dict[str, Any] = {}
        if title := raw.get("title") or raw.get("display_name"):
            data["title"] = normalize_text(title)

        abstract = None
        if abstract_text := raw.get("abstract_text"):
            abstract = abstract_text
        elif raw_abstract := raw.get("abstract"):
            abstract = raw_abstract
        elif inverted_index := raw.get("abstract_inverted_index"):
            abstract = extract_abstract_from_inverted_index(inverted_index)

        if abstract:
            data["abstract"] = normalize_text(abstract)

        if keywords := raw.get("keywords"):
            data["keywords"] = normalize_keywords(keywords)

        if subjects := raw.get("subjects"):
            data["subjects"] = normalize_keywords(subjects)

        if description := raw.get("description"):
            data["description"] = normalize_text(description)

        return data

    def _build_document_fields(self, input_doc: InputDocument) -> dict[str, Any]:
        raise NotImplementedError

    def _build_oca_data_field(self, input_doc: InputDocument) -> dict[str, Any]:
        oca: dict[str, Any] = {"scope": input_doc.scope}
        if scielo := input_doc.scielo_oca():
            oca["scielo"] = scielo
        if openalex := input_doc.openalex_oca():
            oca["openalex"] = openalex
        return oca

    def _build_authorships_field(self, raw_data: dict[str, Any]) -> list:
        authorships = []
        for authorship in raw_data.get("authorships") or []:
            author = authorship.get("author") or {}
            institutions = []

            for inst in authorship.get("institutions") or []:
                country_code = None
                if raw_code := inst.get("country_code"):
                    country_code = normalize_country_code(raw_code)

                institutions.append({
                    "name": inst.get("display_name") or inst.get("name"),
                    "id": inst.get("id"),
                    "ror": inst.get("ror"),
                    "type": inst.get("type"),
                    "country_code": country_code,
                })

            authorships.append({
                "author_position": authorship.get("author_position") or authorship.get("position"),
                "name": author.get("display_name") or authorship.get("raw_author_name") or authorship.get("name"),
                "id": author.get("id") or authorship.get("id"),
                "orcid": author.get("orcid") or authorship.get("orcid"),
                "institutions": institutions,
            })

        return authorships

    def _build_author_country_codes_field(self, raw_data: dict[str, Any], authorships: list) -> list:
        countries = set()
        for code in raw_data.get("author_country_codes") or []:
            if normalized := normalize_country_code(code):
                countries.add(normalized)

        for authorship in raw_data.get("authorships") or []:
            for code in authorship.get("countries") or []:
                if normalized := normalize_country_code(code):
                    countries.add(normalized)

        for authorship in authorships:
            for institution in authorship.get("institutions") or []:
                if code := institution.get("country_code"):
                    if normalized := normalize_country_code(code):
                        countries.add(normalized)

        return sorted(countries)

    def _build_source_field(self, raw_data: dict[str, Any]) -> dict:
        source: dict[str, Any] = {}
        raw_source: dict[str, Any] = {}
        sources = raw_data.get("sources")
        if sources:
            if isinstance(sources, list) and len(sources) > 0:
                raw_source = sources[0]
            elif isinstance(sources, dict):
                raw_source = sources
        else:
            location = raw_data.get("primary_location") or raw_data.get("best_oa_location") or {}
            raw_source = location.get("source") or {}
            source["landing_page_url"] = location.get("landing_page_url")

        source.update({
            "id": raw_source.get("id"),
            "title": raw_source.get("title") or raw_source.get("display_name") or raw_data.get("journal_title"),
            "type": raw_source.get("type") or raw_data.get("primary_source_type"),
            "is_open_access": (
                raw_source.get("is_open_access") if "is_open_access" in raw_source else raw_source.get("is_oa")
            ),
            "issns": raw_source.get("issns") or raw_source.get("issn"),
            "issn_l": raw_source.get("issn_l"),
            "host_organization": raw_source.get("host_organization"),
            "host_organization_name": raw_source.get("host_organization_name"),
        })

        return source

    def _normalize_named_items(self, value: Any) -> list:
        if not value:
            return []
        if isinstance(value, str):
            return [{"name": value}]
        if isinstance(value, dict):
            name = value.get("name") or value.get("display_name")
            return [{"name": name}] if name else []

        items = value if isinstance(value, list) else [value]
        normalized = []

        for item in items:
            if isinstance(item, str):
                normalized.append({"name": item})
            elif isinstance(item, dict):
                name = item.get("name") or item.get("display_name")
                if name:
                    normalized.append({"name": name})

        return normalized

    def _build_metrics_field(self, raw_data: dict[str, Any]) -> dict:
        metrics: dict[str, Any] = {}
        citation_total = raw_data.get("cited_by_count") or raw_data.get("citation_count")
        by_year = [
            {"year": item.get("year"), "total": item.get("cited_by_count") or item.get("total")}
            for item in raw_data.get("counts_by_year") or []
        ]
        if citation_total is not None or by_year:
            metrics["received_citations"] = {"total": citation_total, "by_year": by_year}

        return metrics

    def _build_topics_field(self, raw_data: dict[str, Any]) -> list:
        topics = raw_data.get("topics") or []
        if not topics and raw_data.get("primary_topic"):
            topics = [raw_data["primary_topic"]]
        return [
            {
                "name": topic.get("display_name") or topic.get("name"),
                "domain": extract_display_name(topic.get("domain")),
                "field": extract_display_name(topic.get("field")),
                "subfield": extract_display_name(topic.get("subfield")),
                "score": topic.get("score"),
            }
            for topic in topics
        ]

    def _build_sdgs_field(self, raw_data: dict[str, Any]) -> list:
        return [
            {"id": sdg.get("id"), "display_name": sdg.get("display_name"), "score": sdg.get("score")}
            for sdg in raw_data.get("sustainable_development_goals") or []
        ]

    def _build_funders_field(self, raw_data: dict[str, Any]) -> list:
        funders = []
        for funder in raw_data.get("funders") or []:
            country_code = None
            if raw_code := funder.get("country_code"):
                country_code = normalize_country_code(raw_code)

            funders.append({
                "name": funder.get("display_name") or funder.get("name"),
                "id": funder.get("id"),
                "ror": funder.get("ror"),
                "country_code": country_code,
            })

        return funders

    def _build_awards_field(self, raw_data: dict[str, Any]) -> list:
        return [
            {
                "funder_name": award.get("funder_name"),
                "funder_id": award.get("funder_id"),
                "award_id": award.get("award_id") or award.get("id"),
            }
            for award in raw_data.get("awards") or []
        ]

    def _build_publishers_field(self, raw_data: dict[str, Any]) -> list:
        publishers = list(raw_data.get("publishers") or [])
        location = raw_data.get("primary_location") or raw_data.get("best_oa_location") or {}
        source = location.get("source") or {}
        if not publishers and source.get("host_organization_name"):
            publishers.append({
                "id": source.get("host_organization"),
                "name": source.get("host_organization_name"),
            })

        return publishers

    def _build_content_url_field(self, raw_data: dict[str, Any]) -> Any:
        return first_value(
            raw_data.get("content_url")
            or (raw_data.get("open_access") or {}).get("oa_url")
            or (raw_data.get("primary_location") or {}).get("pdf_url")
            or (raw_data.get("primary_location") or {}).get("landing_page_url")
        )

    def _build_is_open_access_field(self, raw_data: dict[str, Any]) -> Any:
        if "is_open_access" in raw_data:
            return raw_data["is_open_access"]

        return (raw_data.get("open_access") or {}).get("is_oa")

    def _build_open_access_status_field(self, raw_data: dict[str, Any]) -> Any:
        return raw_data.get("open_access_status") or (raw_data.get("open_access") or {}).get("oa_status")

    def _build_biblio_fields(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        biblio = dict(raw_data.get("biblio") or {})
        return {
            "biblio": biblio,
            "volume": biblio.get("volume"),
            "issue": biblio.get("issue"),
            "first_page": biblio.get("first_page"),
            "last_page": biblio.get("last_page"),
        }

    def _build_source_summary_fields(self, source: dict[str, Any]) -> dict[str, Any]:
        return {
            "source_title": source.get("title"),
            "source_issns": source.get("issns") or [],
            "source_type": source.get("type"),
        }

    def _build_citation_fields(self, metrics: dict[str, Any]) -> dict[str, Any]:
        if "total" in metrics.get("received_citations", {}):
            return {"citation_count": metrics["received_citations"]["total"]}
        return {}


class SciELOStandardizer(BaseStandardizer):

    def _build_identifier_fields(self, input_doc: InputDocument) -> dict[str, Any]:
        raw_doc = dict(input_doc.source_payload)
        raw_doc.pop("id", None)
        if input_doc.doi:
            raw_doc["doi"] = input_doc.doi
        if scielo_id := input_doc.scielo_oca().get("pid_v2"):
            raw_doc["scielo_id"] = scielo_id
        return extract_identifiers(raw_doc)

    def _build_document_fields(self, input_doc: InputDocument) -> dict[str, Any]:
        data: dict[str, Any] = {}
        raw = input_doc.source_payload

        data["language"] = self._build_language_field(raw)
        data["publication_date"] = input_doc.publication_date or raw.get("publication_date")
        data["title_with_lang"] = raw.get("title_with_lang") or []
        data["abstract_with_lang"] = self._build_abstract_with_lang_field(raw)
        data["description_with_lang"] = self._build_description_with_lang_field(raw)
        data["keywords_with_lang"] = raw.get("keywords_with_lang") or []
        data["subjects_with_lang"] = raw.get("subjects_with_lang") or []
        data["content_url"] = self._build_content_url_field(raw)
        data["content_url_with_lang"] = self._build_content_url_with_lang_field(raw)
        data["is_open_access"] = self._build_is_open_access_field(raw)
        data["open_access_status"] = self._build_open_access_status_field(raw)
        data.update(self._build_biblio_fields(raw))
        data["parent_book"] = self._build_parent_book_field(raw)

        data["authorships"] = self._build_authorships_field(raw)
        data["author_country_codes"] = sorted(
            self._build_author_country_codes_field(raw, data["authorships"])
        )

        data["funders"] = self._build_funders_field(raw)
        data["awards"] = self._build_awards_field(raw)
        data["publishers"] = self._build_publishers_field(raw)

        data["source"] = self._build_source_field(raw)
        data.update(self._build_source_summary_fields(data["source"]))

        data["topic"] = self._build_topics_field(raw)
        data["topics"] = data["topic"]
        data["sustainable_development_goals"] = self._build_sdgs_field(raw)
        data["referenced_works"] = self._build_referenced_works_field(raw)
        data["metrics"] = self._build_metrics_field(raw)
        data.update(self._build_citation_fields(data["metrics"]))
        data["indexed_in"] = self._build_indexed_in_field(raw)

        return data

    def _build_language_field(self, raw_data: dict[str, Any]) -> list[str] | None:
        languages: set[str] = set()
        scl_langs = raw_data.get("languages") or raw_data.get("language") or []
        if isinstance(scl_langs, str):
            scl_langs = [scl_langs]
        for l in scl_langs:
            if l and (normalized := normalize_language(l)):
                languages.add(normalized)

        return sorted(languages) if languages else None

    def _fallback_language_code(self, raw_data: dict[str, Any]) -> str:
        lang = raw_data.get("language") or raw_data.get("languages") or "und"
        if isinstance(lang, list):
            lang = next((item for item in lang if item), "und")

        return str(lang).strip().lower() or "und"

    def _build_abstract_with_lang_field(self, raw_data: dict[str, Any]) -> list[dict[str, Any]]:
        abstracts_map: dict[str, str] = {
            item.get("language"): item.get("abstract") or item.get("text")
            for item in raw_data.get("abstract_with_lang") or []
            if item.get("language") and (item.get("abstract") or item.get("text"))
        }
        if not abstracts_map and raw_data.get("abstract"):
            abstracts_map[self._fallback_language_code(raw_data)] = raw_data["abstract"]

        return [
            {"language": l, "abstract": a} for l, a in sorted(abstracts_map.items())
        ]

    def _build_description_with_lang_field(self, raw_data: dict[str, Any]) -> list[dict[str, Any]]:
        description_map: dict[str, str] = {
            item.get("language"): item.get("description") or item.get("text")
            for item in raw_data.get("description_with_lang") or []
            if item.get("language") and (item.get("description") or item.get("text"))
        }
        if not description_map and raw_data.get("description"):
            description_map[self._fallback_language_code(raw_data)] = raw_data["description"]
        return [
            {"language": l, "description": d} for l, d in sorted(description_map.items())
        ]

    def _build_content_url_with_lang_field(self, raw_data: dict[str, Any]) -> list[dict[str, Any]]:
        urls_map: dict[str, str] = {
            item.get("language"): item.get("content_url")
            for item in raw_data.get("content_url_with_lang") or []
            if item.get("language") and item.get("content_url")
        }
        if raw_data.get("content_url") and not urls_map:
            urls_map[self._fallback_language_code(raw_data)] = self._build_content_url_field(raw_data)

        return [
            {"language": l, "content_url": u} for l, u in sorted(urls_map.items())
        ]

    def _build_subjects_with_lang_field(self, raw_data: dict[str, Any]) -> list[dict[str, Any]]:
        subjects_map: dict[str, list[str]] = {}
        for item in raw_data.get("subjects_with_lang") or []:
            if not isinstance(item, dict):
                continue
            lang = item.get("language")
            value = item.get("subjects") or item.get("text")
            if lang and value:
                values = [value] if isinstance(value, str) else as_list(value)
                subjects_map.setdefault(lang, []).extend(values)
        if not subjects_map and raw_data.get("subjects"):
            lang = self._fallback_language_code(raw_data)
            subjects_map[lang] = normalize_keywords(raw_data["subjects"])
        result = []
        for lang in sorted(subjects_map):
            for subject in subjects_map[lang]:
                result.append({"language": lang, "subjects": subject})
        return result

    def _build_referenced_works_field(self, raw_data: dict[str, Any]) -> list:
        return (
            raw_data.get("referenced_works")
            or raw_data.get("references")
            or raw_data.get("reference")
            or raw_data.get("refs")
            or []
        )

    def _build_indexed_in_field(self, raw_data: dict[str, Any]) -> list[str]:
        indexed_in: list[str] = []
        if index_raw := raw_data.get("indexed_in"):
            if isinstance(index_raw, str):
                indexed_in = [index_raw]
            else:
                indexed_in = list(index_raw)
        return sorted(set(indexed_in)) if indexed_in else []

    def _build_parent_book_field(self, raw_data: dict[str, Any]) -> dict:
        return {}


class OpenAlexStandardizer(BaseStandardizer):

    def _build_identifier_fields(self, input_doc: InputDocument) -> dict[str, Any]:
        identifiers = super()._build_identifier_fields(input_doc)
        if openalex_id := normalize_openalex_id(input_doc.source_payload["id"]):
            identifiers["openalex_id"] = openalex_id
        return identifiers

    def _build_ids_field(self, data: dict[str, Any], raw: dict[str, Any]) -> dict[str, Any]:
        ids = super()._build_ids_field(data, raw)
        openalex_id = normalize_openalex_id(raw["id"])
        if openalex_id:
            ids["openalex"] = openalex_id
            if raw.get("language"):
                ids["openalex_with_lang"] = [
                    {"language": raw["language"], "openalex": openalex_id}
                ]
        return ids

    def _build_document_fields(self, input_doc: InputDocument) -> dict[str, Any]:
        data: dict[str, Any] = {}
        raw = input_doc.source_payload

        data["language"] = self._build_language_field(input_doc)
        data["publication_date"] = input_doc.publication_date or raw.get("publication_date")
        data["title_with_lang"] = []
        data["abstract_with_lang"] = self._build_abstract_with_lang_field(input_doc)
        data["description_with_lang"] = []
        data["keywords_with_lang"] = []
        data["subjects_with_lang"] = []
        data["content_url"] = self._build_content_url_field(raw)
        data["content_url_with_lang"] = self._build_content_url_with_lang_field(input_doc)
        data["is_open_access"] = self._build_is_open_access_field(raw)
        data["open_access_status"] = self._build_open_access_status_field(raw)
        data.update(self._build_biblio_fields(raw))
        data["parent_book"] = {}

        data["authorships"] = self._build_authorships_field(raw)
        data["author_country_codes"] = sorted(
            self._build_author_country_codes_field(raw, data["authorships"])
        )

        data["funders"] = self._build_funders_field(raw)
        data["awards"] = self._build_awards_field(raw)
        data["publishers"] = self._build_publishers_field(raw)

        data["source"] = self._build_source_field(raw)
        data.update(self._build_source_summary_fields(data["source"]))

        data["topic"] = self._build_topics_field(raw)
        data["topics"] = data["topic"]
        data["sustainable_development_goals"] = self._build_sdgs_field(raw)
        data["referenced_works"] = raw.get("referenced_works") or []
        data["metrics"] = self._build_metrics_field(raw)
        data.update(self._build_citation_fields(data["metrics"]))
        data["indexed_in"] = self._build_indexed_in_field(input_doc)

        return data

    def _build_language_field(self, input_doc: InputDocument) -> list[str] | None:
        languages: set[str] = set()
        for oa in input_doc.enrichment_payloads():
            if oa_lang := oa.get("language"):
                if normalized := normalize_language(oa_lang):
                    languages.add(normalized)

        return sorted(languages) if languages else None

    def _build_abstract_with_lang_field(self, input_doc: InputDocument) -> list[dict[str, Any]]:
        raw = input_doc.source_payload
        abstracts_map: dict[str, str] = {}
        for oa in input_doc.enrichment_payloads():
            lang = oa.get("language", "und")
            if lang not in abstracts_map and (idx := oa.get("abstract_inverted_index")):
                abstracts_map[lang] = extract_abstract_from_inverted_index(idx)
        if raw.get("abstract") and not abstracts_map:
            abstracts_map[raw.get("language", "und")] = raw["abstract"]
        return [
            {"language": l, "abstract": a} for l, a in sorted(abstracts_map.items())
        ]

    def _build_content_url_with_lang_field(self, input_doc: InputDocument) -> list[dict[str, Any]]:
        urls_map: dict[str, str] = {}
        for oa in input_doc.enrichment_payloads():
            lang = oa.get("language", "und")
            if lang not in urls_map:
                if oa_url := self._build_content_url_field(oa):
                    urls_map[lang] = oa_url
        return [
            {"language": l, "content_url": u} for l, u in sorted(urls_map.items())
        ]

    def _build_indexed_in_field(self, input_doc: InputDocument) -> list[str]:
        indexed_in: list[str] = []
        for oa in input_doc.enrichment_payloads():
            oa_indexed = oa.get("indexed_in") or []
            if isinstance(oa_indexed, str):
                oa_indexed = [oa_indexed]
            for x in oa_indexed:
                if x:
                    indexed_in.append(str(x).strip().lower())
        return sorted(set(indexed_in)) if indexed_in else []


class SciELOBookStandardizer(SciELOStandardizer):

    def _build_parent_book_field(self, raw_data: dict[str, Any]) -> dict:
        monograph = raw_data.get("monograph")
        if not isinstance(monograph, dict) or not monograph:
            return {}

        ids = {}
        if monograph.get("id"):
            ids["scl_book_id"] = monograph["id"]
        for key in ("doi", "isbn", "eisbn"):
            if monograph.get(key):
                ids[key] = monograph[key]

        publishers = self._normalize_named_items(monograph.get("publishers"))
        authorships = [
            {
                "role": item.get("role"),
                "name": item.get("name"),
                "orcid": item.get("orcid") or item.get("link_resume"),
            }
            for item in monograph.get("authorships") or []
            if isinstance(item, dict)
        ]

        return {
            "id": monograph.get("id"),
            "title": monograph.get("title"),
            "publication_year": int_or_none(monograph.get("publication_year")),
            "language": monograph.get("language"),
            "ids": ids,
            "publishers": publishers,
            "authorships": authorships,
        }
