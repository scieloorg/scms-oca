import logging
from typing import Any

from etl.indexing.contracts import BronzeDocument, SilverDocument
from etl.transform.extractors import (
    display_name,
    first_value,
    match_key,
    normalize_identifiers,
    rebuild_abstract_from_inverted_index,
)
from etl.transform.normalizers import (
    as_list,
    int_or_none,
    normalize_keywords,
    normalize_text,
    stz_country_code,
    stz_doi,
    stz_language,
)

logger = logging.getLogger(__name__)


class DefaultStandardizer:

    def __init__(self):
        self.steps = [
            self._normalize_basic_fields,
            self._normalize_identifiers_step,
            self._normalize_text_fields,
            self._normalize_rich_fields,
            self._normalize_metadata,
        ]

    def run(self, bronze_doc: BronzeDocument) -> SilverDocument:
        silver_data: dict[str, Any] = {}
        for step in self.steps:
            try:
                silver_data = step(silver_data, bronze_doc)
            except Exception as e:
                logger.error(f"Error in step {step.__name__}: {e}", exc_info=True)
                raise

        try:
            return SilverDocument(**silver_data)
        except Exception as e:
            logger.error(f"Failed to create SilverDocument: {e}")
            raise

    def _normalize_basic_fields(
        self,
        data: dict[str, Any],
        bronze: BronzeDocument,
    ) -> dict[str, Any]:
        data["doc_id"] = bronze.doc_id
        data["type"] = bronze.document_type
        data["publication_year"] = bronze.publication_year
        data["publication_date"] = bronze.publication_date
        return data

    def _normalize_identifiers_step(
        self,
        data: dict[str, Any],
        bronze: BronzeDocument,
    ) -> dict[str, Any]:
        raw_doc: dict[str, Any] = {}

        if bronze.doi:
            raw_doc["doi"] = bronze.doi

        if bronze.raw_openalex_data:
            raw_doc.update(bronze.raw_openalex_data)

        if bronze.raw_scielo_data:
            raw_scielo = dict(bronze.raw_scielo_data)
            raw_scielo.pop("id", None)
            raw_doc.update(raw_scielo)
            if bronze.pid_v2:
                raw_doc["scielo_id"] = bronze.pid_v2

        identifiers = normalize_identifiers(raw_doc)
        data.update(identifiers)
        return data

    def _normalize_text_fields(
        self,
        data: dict[str, Any],
        bronze: BronzeDocument,
    ) -> dict[str, Any]:
        raw_data = bronze.raw_openalex_data or bronze.raw_scielo_data or {}

        if title := raw_data.get("title") or raw_data.get("display_name"):
            data["title"] = normalize_text(title)

        abstract = None
        if abstract_text := raw_data.get("abstract_text"):
            abstract = abstract_text
        elif raw_abstract := raw_data.get("abstract"):
            abstract = raw_abstract
        elif inverted_index := raw_data.get("abstract_inverted_index"):
            abstract = rebuild_abstract_from_inverted_index(inverted_index)

        if abstract:
            data["abstract"] = normalize_text(abstract)

        if keywords := raw_data.get("keywords"):
            data["keywords"] = normalize_keywords(keywords)

        if subjects := raw_data.get("subjects"):
            data["subjects"] = normalize_keywords(subjects)

        if description := raw_data.get("description"):
            data["description"] = normalize_text(description)

        return data

    def _normalize_metadata(
        self,
        data: dict[str, Any],
        bronze: BronzeDocument,
    ) -> dict[str, Any]:
        indexed_in: list[str] = []

        if bronze.raw_openalex_data:
            oa_indexed = bronze.raw_openalex_data.get("indexed_in") or []
            if isinstance(oa_indexed, str):
                oa_indexed = [oa_indexed]
            for x in oa_indexed:
                if x:
                    indexed_in.append(str(x).strip().lower())

        if indexed_in:
            data["indexed_in"] = sorted(set(indexed_in))

        oca_data = {
            "scope": self._determine_scope(bronze),
        }
        if bronze.raw_scielo_data:
            oca_data["scielo"] = self._build_scielo_oca_data(bronze)
        if bronze.raw_openalex_data:
            oca_data["openalex"] = self._build_openalex_oca_data(bronze.raw_openalex_data)

        if bronze.oca_data:
            oca_data.update(bronze.oca_data)
            if isinstance(oca_data.get("scope"), str):
                oca_data["scope"] = [oca_data["scope"]]

        data["oca_data"] = oca_data
        return data

    def _normalize_rich_fields(
        self,
        data: dict[str, Any],
        bronze: BronzeDocument,
    ) -> dict[str, Any]:
        raw_scielo = bronze.raw_scielo_data or {}
        raw_oa = bronze.raw_openalex_data or {}
        oa_records = bronze.openalex_consolidated or []
        if not oa_records and raw_oa:
            oa_records = [raw_oa]

        data["ids"] = self._extract_ids(data, raw_scielo or raw_oa)
        if raw_scielo and raw_oa:
            data["ids"] = {
                **data["ids"],
                **self._extract_ids(data, raw_oa),
                **self._extract_ids(data, raw_scielo),
            }

        languages: set[str] = set()

        if bronze.raw_scielo_data:
            scl_langs = raw_scielo.get("languages") or raw_scielo.get("language") or []
            if isinstance(scl_langs, str):
                scl_langs = [scl_langs]
            for l in scl_langs:
                if l and (normalized := stz_language(l)):
                    languages.add(normalized)

        for oa in oa_records:
            if oa_lang := oa.get("language"):
                if normalized := stz_language(oa_lang):
                    languages.add(normalized)

        data["language"] = sorted(languages) if languages else None

        data["publication_date"] = (
            data.get("publication_date")
            or raw_scielo.get("publication_date")
            or raw_oa.get("publication_date")
        )

        data["title_with_lang"] = raw_scielo.get("title_with_lang") or []

        abstracts_map: dict[str, str] = {
            item.get("language"): item.get("abstract") or item.get("text")
            for item in raw_scielo.get("abstract_with_lang") or []
            if item.get("language") and (item.get("abstract") or item.get("text"))
        }
        if not abstracts_map and raw_scielo.get("abstract"):
            lang = raw_scielo.get("language") or raw_scielo.get("languages") or "und"
            if isinstance(lang, list):
                lang = next((item for item in lang if item), "und")
            abstracts_map[str(lang).strip().lower() or "und"] = raw_scielo["abstract"]
        for oa in oa_records:
            lang = oa.get("language", "und")
            if lang not in abstracts_map and (idx := oa.get("abstract_inverted_index")):
                abstracts_map[lang] = rebuild_abstract_from_inverted_index(idx)

        data["abstract_with_lang"] = [
            {"language": l, "abstract": a} for l, a in sorted(abstracts_map.items())
        ]

        description_map: dict[str, str] = {
            item.get("language"): item.get("description") or item.get("text")
            for item in raw_scielo.get("description_with_lang") or []
            if item.get("language") and (item.get("description") or item.get("text"))
        }
        if not description_map and raw_scielo.get("description"):
            lang = raw_scielo.get("language") or raw_scielo.get("languages") or "und"
            if isinstance(lang, list):
                lang = next((item for item in lang if item), "und")
            description_map[str(lang).strip().lower() or "und"] = raw_scielo["description"]
        data["description_with_lang"] = [
            {"language": l, "description": d} for l, d in sorted(description_map.items())
        ]

        data["keywords_with_lang"] = raw_scielo.get("keywords_with_lang") or []
        data["subjects_with_lang"] = raw_scielo.get("subjects_with_lang") or []

        data["content_url"] = self._extract_content_url(raw_scielo or raw_oa)

        urls_map: dict[str, str] = {
            item.get("language"): item.get("content_url")
            for item in raw_scielo.get("content_url_with_lang") or []
            if item.get("language") and item.get("content_url")
        }
        if raw_scielo.get("content_url") and not urls_map:
            lang = raw_scielo.get("language") or raw_scielo.get("languages") or "und"
            if isinstance(lang, list):
                lang = next((item for item in lang if item), "und")
            urls_map[str(lang).strip().lower() or "und"] = self._extract_content_url(raw_scielo)
        for oa in oa_records:
            lang = oa.get("language", "und")
            if lang not in urls_map:
                if oa_url := self._extract_content_url(oa):
                    urls_map[lang] = oa_url

        data["content_url_with_lang"] = [
            {"language": l, "content_url": u} for l, u in sorted(urls_map.items())
        ]

        data["is_open_access"] = self._extract_is_open_access(raw_scielo or raw_oa)
        data["open_access_status"] = self._extract_open_access_status(raw_scielo or raw_oa)

        data["biblio"] = dict(raw_scielo.get("biblio") or raw_oa.get("biblio") or {})
        data.update({
            "volume": data["biblio"].get("volume"),
            "issue": data["biblio"].get("issue"),
            "first_page": data["biblio"].get("first_page"),
            "last_page": data["biblio"].get("last_page"),
        })

        data["parent_book"] = self._extract_parent_book(raw_scielo)

        data["authorships"] = self._merge_authorships(
            self._extract_authorships(raw_scielo),
            self._extract_authorships(raw_oa),
        )

        data["author_country_codes"] = sorted(
            set(
                self._extract_author_country_codes(raw_scielo, data["authorships"])
                + self._extract_author_country_codes(raw_oa, data["authorships"])
            )
        )

        data["funders"] = self._extract_funders(raw_scielo or raw_oa)
        data["awards"] = self._extract_awards(raw_scielo or raw_oa)

        data["publishers"] = self._merge_named_items(
            self._extract_publishers(raw_scielo),
            self._extract_publishers(raw_oa),
        )

        data["source"] = self._merge_source(
            self._extract_source(raw_scielo),
            self._extract_source(raw_oa),
        )
        data.update({
            "source_title": data["source"].get("title"),
            "source_issns": data["source"].get("issns") or [],
            "source_type": data["source"].get("type"),
        })

        data["topic"] = self._extract_topics(raw_scielo or raw_oa)
        data["topics"] = data["topic"]
        data["sustainable_development_goals"] = self._extract_sdgs(raw_scielo or raw_oa)
        data["referenced_works"] = (
            raw_scielo.get("referenced_works")
            or raw_scielo.get("references")
            or raw_scielo.get("reference")
            or raw_scielo.get("refs")
            or raw_oa.get("referenced_works")
            or []
        )
        data["metrics"] = self._extract_metrics(raw_scielo or raw_oa)

        if "total" in data["metrics"].get("received_citations", {}):
            data["citation_count"] = data["metrics"]["received_citations"]["total"]

        return data

    def _determine_scope(self, bronze: BronzeDocument) -> list:
        scope = []
        if bronze.raw_scielo_data:
            scope.append("scielo")
        if bronze.raw_openalex_data:
            scope.append("openalex")
        return scope if scope else ["unknown"]

    def _extract_ids(self, data: dict[str, Any], raw_data: dict[str, Any]) -> dict:
        ids = dict(raw_data.get("ids") or {})
        if ids.get("doi"):
            normalized_doi = stz_doi(ids["doi"])
            if normalized_doi:
                ids["doi"] = normalized_doi
            else:
                ids.pop("doi", None)

        for source_key, target_key in {
            "doi": "doi",
            "mag": "mag",
            "pmcid": "pmcid",
            "pmid": "pmid",
            "openalex_id": "openalex",
            "scielo_id": "scielo",
        }.items():
            if data.get(source_key):
                ids[target_key] = data[source_key]

        if raw_data.get("doi_with_lang"):
            ids["doi_with_lang"] = self._normalize_doi_lang_items(raw_data["doi_with_lang"])
        elif ids.get("doi_with_lang"):
            ids["doi_with_lang"] = self._normalize_doi_lang_items(ids["doi_with_lang"])
        elif raw_data.get("doi") and raw_data.get("language"):
            if normalized_doi := stz_doi(raw_data["doi"]):
                ids["doi_with_lang"] = [{"language": raw_data["language"], "doi": normalized_doi}]

        openalex_id = ids.get("openalex") or raw_data.get("id") or data.get("openalex_id")
        if raw_data.get("openalex_with_lang"):
            ids["openalex_with_lang"] = raw_data["openalex_with_lang"]
        elif openalex_id and raw_data.get("language"):
            ids["openalex_with_lang"] = [{"language": raw_data["language"], "openalex": openalex_id}]

        return ids

    def _normalize_doi_lang_items(self, items: Any) -> list:
        normalized = []
        for item in items or []:
            if not isinstance(item, dict):
                continue
            doi = stz_doi(item.get("doi") or item.get("id") or item.get("value"))
            if doi:
                normalized.append({"language": item.get("language"), "doi": doi})
        return normalized

    def _extract_authorships(self, raw_data: dict[str, Any]) -> list:
        authorships = []
        for authorship in raw_data.get("authorships") or []:
            author = authorship.get("author") or {}
            institutions = []
            for inst in authorship.get("institutions") or []:
                country_code = None
                if raw_code := inst.get("country_code"):
                    country_code = stz_country_code(raw_code)
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

    def _merge_authorships(self, primary: list, enrichment: list) -> list:
        if not primary:
            return enrichment

        merged = [dict(item) for item in primary]
        for oa_item in enrichment:
            match = self._find_matching_authorship(merged, oa_item)
            if not match:
                merged.append(oa_item)
                continue
            for key in ("id", "orcid"):
                if oa_item.get(key) and not match.get(key):
                    match[key] = oa_item[key]
            match["institutions"] = self._merge_named_items(
                match.get("institutions") or [],
                oa_item.get("institutions") or [],
            )
        return merged

    def _find_matching_authorship(self, candidates: list, item: dict) -> dict | None:
        item_position = item.get("author_position")
        item_name = match_key(item.get("name"))
        for candidate in candidates:
            if item_position and candidate.get("author_position") == item_position:
                return candidate
            if item_name and match_key(candidate.get("name")) == item_name:
                return candidate
        return None

    def _extract_author_country_codes(self, raw_data: dict[str, Any], authorships: list) -> list:
        countries = set()

        for code in raw_data.get("author_country_codes") or []:
            if normalized := stz_country_code(code):
                countries.add(normalized)

        for authorship in raw_data.get("authorships") or []:
            for code in authorship.get("countries") or []:
                if normalized := stz_country_code(code):
                    countries.add(normalized)

        for authorship in authorships:
            for institution in authorship.get("institutions") or []:
                if code := institution.get("country_code"):
                    if normalized := stz_country_code(code):
                        countries.add(normalized)

        return sorted(countries)

    def _extract_source(self, raw_data: dict[str, Any]) -> dict:
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

    def _merge_source(self, primary: dict, enrichment: dict) -> dict:
        if not primary:
            return enrichment
        if not enrichment:
            return primary

        merged = dict(primary)
        if enrichment.get("id"):
            merged["id"] = enrichment["id"]
        for key, value in enrichment.items():
            if key == "issns":
                merged["issns"] = sorted(set(as_list(merged.get("issns")) + as_list(value)))
            elif value not in (None, [], {}) and not merged.get(key):
                merged[key] = value
        return merged

    def _extract_parent_book(self, raw_data: dict[str, Any]) -> dict:
        return {}

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

    def _merge_named_items(self, primary: list, enrichment: list) -> list:
        merged = [dict(item) for item in primary]
        for item in enrichment:
            match = self._find_matching_named_item(merged, item)
            if not match and len(merged) == 1 and len(enrichment) == 1:
                match = merged[0]
            if not match:
                merged.append(item)
                continue
            for key, value in item.items():
                if value not in (None, [], {}) and not match.get(key):
                    match[key] = value
        return merged

    def _find_matching_named_item(self, candidates: list, item: dict) -> dict | None:
        item_id = item.get("id") or item.get("ror")
        item_name = match_key(item.get("name") or item.get("display_name"))
        for candidate in candidates:
            candidate_id = candidate.get("id") or candidate.get("ror")
            if item_id and candidate_id == item_id:
                return candidate
            candidate_name = match_key(candidate.get("name") or candidate.get("display_name"))
            if item_name and candidate_name == item_name:
                return candidate
        return None

    def _extract_metrics(self, raw_data: dict[str, Any]) -> dict:
        metrics: dict[str, Any] = {}
        citation_total = raw_data.get("cited_by_count") or raw_data.get("citation_count")
        by_year = [
            {"year": item.get("year"), "total": item.get("cited_by_count") or item.get("total")}
            for item in raw_data.get("counts_by_year") or []
        ]
        if citation_total is not None or by_year:
            metrics["received_citations"] = {"total": citation_total, "by_year": by_year}
        return metrics

    def _extract_topics(self, raw_data: dict[str, Any]) -> list:
        topics = raw_data.get("topics") or []
        if not topics and raw_data.get("primary_topic"):
            topics = [raw_data["primary_topic"]]
        return [
            {
                "name": topic.get("display_name") or topic.get("name"),
                "domain": display_name(topic.get("domain")),
                "field": display_name(topic.get("field")),
                "subfield": display_name(topic.get("subfield")),
                "score": topic.get("score"),
            }
            for topic in topics
        ]

    def _extract_sdgs(self, raw_data: dict[str, Any]) -> list:
        return [
            {"id": sdg.get("id"), "display_name": sdg.get("display_name"), "score": sdg.get("score")}
            for sdg in raw_data.get("sustainable_development_goals") or []
        ]

    def _extract_funders(self, raw_data: dict[str, Any]) -> list:
        funders = []
        for funder in raw_data.get("funders") or []:
            country_code = None
            if raw_code := funder.get("country_code"):
                country_code = stz_country_code(raw_code)
            funders.append({
                "name": funder.get("display_name") or funder.get("name"),
                "id": funder.get("id"),
                "ror": funder.get("ror"),
                "country_code": country_code,
            })
        return funders

    def _extract_awards(self, raw_data: dict[str, Any]) -> list:
        return [
            {
                "funder_name": award.get("funder_name"),
                "funder_id": award.get("funder_id"),
                "award_id": award.get("award_id") or award.get("id"),
            }
            for award in raw_data.get("awards") or []
        ]

    def _extract_publishers(self, raw_data: dict[str, Any]) -> list:
        publishers = list(raw_data.get("publishers") or [])
        location = raw_data.get("primary_location") or raw_data.get("best_oa_location") or {}
        source = location.get("source") or {}
        if not publishers and source.get("host_organization_name"):
            publishers.append({
                "id": source.get("host_organization"),
                "name": source.get("host_organization_name"),
            })
        return publishers

    def _build_scielo_oca_data(self, bronze: BronzeDocument) -> dict:
        raw = bronze.raw_scielo_data or {}

        collections = bronze.scielo_collections or as_list(bronze.collection or raw.get("collection"))
        pids = bronze.scielo_pids or as_list(bronze.pid_v2 or raw.get("pid_v2") or raw.get("code"))
        scielo_type = raw.get("type") or raw.get("document_type") or bronze.document_type

        return {
            "ids": pids,
            "collection": collections if len(collections) > 1 else (collections[0] if collections else None),
            "pid_v2": pids if len(pids) > 1 else (pids[0] if pids else None),
            "type": scielo_type,
            "source": {
                "country_code": stz_country_code(raw.get("country_code")),
                "indexed_in": raw.get("indexed_in"),
            },
        }

    def _build_openalex_oca_data(self, raw_data: dict[str, Any]) -> dict:
        version = {
            "id": raw_data.get("id"),
            "doi": raw_data.get("doi"),
            "title": raw_data.get("title") or raw_data.get("display_name"),
            "language": raw_data.get("language"),
            "content_url": self._extract_content_url(raw_data),
            "is_open_access": self._extract_is_open_access(raw_data),
            "open_access_status": self._extract_open_access_status(raw_data),
            "metrics": self._extract_metrics(raw_data),
        }
        ids = raw_data.get("ids") or {}
        openalex_ids = [value for value in (ids.get("openalex"), raw_data.get("id")) if value]
        return {"ids": list(dict.fromkeys(openalex_ids)), "versions": [version]}

    def _extract_content_url(self, raw_data: dict[str, Any]) -> Any:
        return first_value(
            raw_data.get("content_url")
            or (raw_data.get("open_access") or {}).get("oa_url")
            or (raw_data.get("primary_location") or {}).get("pdf_url")
            or (raw_data.get("primary_location") or {}).get("landing_page_url")
        )

    def _extract_is_open_access(self, raw_data: dict[str, Any]) -> Any:
        if "is_open_access" in raw_data:
            return raw_data["is_open_access"]
        return (raw_data.get("open_access") or {}).get("is_oa")

    def _extract_open_access_status(self, raw_data: dict[str, Any]) -> Any:
        return raw_data.get("open_access_status") or (raw_data.get("open_access") or {}).get("oa_status")


class BookStandardizer(DefaultStandardizer):

    def _extract_parent_book(self, raw_data: dict[str, Any]) -> dict:
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
