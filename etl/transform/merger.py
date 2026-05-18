import logging

from etl.documents import SilverDocument
from etl.transform.normalizers import normalize_author_name, normalize_language
from etl.transform.utils import as_list, scalar_or_list, unique

logger = logging.getLogger(__name__)


class SilverMerger:
    def merge(
        self,
        scielo_docs: list[SilverDocument],
        openalex_matches: list[tuple[SilverDocument, str, float, dict]],
    ) -> SilverDocument:
        if not scielo_docs:
            raise ValueError("At least one SciELO document is required")

        logger.info(
            "Merging %s SciELO doc(s) with %s OpenAlex match(es)",
            len(scielo_docs),
            len(openalex_matches),
        )

        base_scielo = self._consolidate_scielo_documents(scielo_docs)
        openalex_docs = [match[0] for match in openalex_matches]

        if openalex_docs:
            merged = self._enrich_scielo_with_openalex(base_scielo, openalex_docs)
        else:
            merged = base_scielo
            merged.oca_data.setdefault("scope", []).append("scielo")

        return self._with_merge_trace(merged, scielo_docs, openalex_matches)

    def _same_author(self, scielo_author: dict, openalex_author: dict) -> bool:
        sc_name = normalize_author_name(scielo_author.get("name", ""))
        oa_name = normalize_author_name(openalex_author.get("name", ""))
        if sc_name and oa_name and sc_name == oa_name:
            return True

        sc_orcid = scielo_author.get("orcid")
        oa_orcid = openalex_author.get("orcid")
        if sc_orcid and oa_orcid and sc_orcid == oa_orcid:
            return True

        sc_id = scielo_author.get("id")
        oa_id = openalex_author.get("id")
        if sc_id and oa_id and sc_id == oa_id:
            return True

        return False

    def _merge_author_institutions(
        self,
        scielo_institutions: list,
        openalex_institutions: list,
    ) -> list:
        if not openalex_institutions:
            return list(scielo_institutions)

        existing_ids = {
            inst.get("id")
            for inst in scielo_institutions
            if isinstance(inst, dict) and inst.get("id")
        }
        existing_rors = {
            inst.get("ror")
            for inst in scielo_institutions
            if isinstance(inst, dict) and inst.get("ror")
        }
        existing_names = {
            normalize_author_name(inst.get("name", ""))
            for inst in scielo_institutions
            if isinstance(inst, dict) and inst.get("name")
        }

        merged = list(scielo_institutions)
        for oa_inst in openalex_institutions:
            if not isinstance(oa_inst, dict):
                continue

            inst_id = oa_inst.get("id")
            ror = oa_inst.get("ror")
            oa_name = normalize_author_name(oa_inst.get("name", ""))
            if (
                (inst_id and inst_id in existing_ids)
                or (ror and ror in existing_rors)
                or (oa_name and oa_name in existing_names)
            ):
                continue

            merged.append(oa_inst)
            if inst_id:
                existing_ids.add(inst_id)
            if ror:
                existing_rors.add(ror)
            if oa_name:
                existing_names.add(oa_name)

        return merged

    def _merge_authorships(
        self,
        scielo_authorships: list,
        openalex_authorships: list,
    ) -> list:
        enriched = []
        matched_oa_indices = set()

        for sc_author in scielo_authorships:
            enriched_author = dict(sc_author)

            best_match = None
            best_match_idx = None
            for idx, oa_author in enumerate(openalex_authorships):
                if idx in matched_oa_indices:
                    continue
                if self._same_author(sc_author, oa_author):
                    best_match = oa_author
                    best_match_idx = idx
                    break

            if best_match:
                matched_oa_indices.add(best_match_idx)
                if not enriched_author.get("id") and best_match.get("id"):
                    enriched_author["id"] = best_match["id"]
                if not enriched_author.get("orcid") and best_match.get("orcid"):
                    enriched_author["orcid"] = best_match["orcid"]
                enriched_author["institutions"] = self._merge_author_institutions(
                    enriched_author.get("institutions", []),
                    best_match.get("institutions", []),
                )

            enriched.append(enriched_author)

        for idx, oa_author in enumerate(openalex_authorships):
            if idx not in matched_oa_indices:
                if not any(self._same_author(enr_author, oa_author) for enr_author in enriched):
                    enriched.append(dict(oa_author))

        return enriched

    def _openalex_ids(self, doc: SilverDocument) -> list:
        ids = []
        if doc.openalex_id:
            ids.append(doc.openalex_id)

        indexed_ids = doc.ids or {}
        ids.extend(as_list(indexed_ids.get("openalex")))

        openalex = (doc.oca_data or {}).get("openalex") or {}
        ids.extend(as_list(openalex.get("ids")))

        return unique(
            [value for value in ids if isinstance(value, str) and "openalex.org/W" in value]
        )

    def _scielo_ids(self, doc: SilverDocument) -> list:
        ids = []
        if doc.scielo_id:
            ids.append(doc.scielo_id)

        indexed_ids = doc.ids or {}
        ids.extend(as_list(indexed_ids.get("scielo")))

        scielo = (doc.oca_data or {}).get("scielo") or {}
        ids.extend(as_list(scielo.get("ids")))
        ids.extend(as_list(scielo.get("pid_v2")))

        return unique(ids)

    def _scielo_collections(self, doc: SilverDocument) -> list:
        scielo = (doc.oca_data or {}).get("scielo") or {}
        return unique(as_list(scielo.get("collection")))

    def _consolidate_scielo_documents(
        self,
        scielo_docs: list[SilverDocument],
    ) -> SilverDocument:
        if len(scielo_docs) == 1:
            return scielo_docs[0]

        logger.debug("Consolidating %s SciELO duplicates", len(scielo_docs))

        base_data = scielo_docs[0].to_dict()
        all_collections = []
        all_pids = []
        all_titles = {}
        all_abstracts = {}
        all_keywords = {}
        all_urls = []

        for doc in scielo_docs:
            data = doc.to_dict()
            scielo_info = (data.get("oca_data") or {}).get("scielo", {})

            if scielo_info.get("collection"):
                collections = (
                    scielo_info["collection"]
                    if isinstance(scielo_info["collection"], list)
                    else [scielo_info["collection"]]
                )
                all_collections.extend(collections)

            if doc.scielo_id:
                all_pids.append(doc.scielo_id)
            pids = scielo_info.get("ids", []) or scielo_info.get("pid_v2", [])
            if isinstance(pids, list):
                all_pids.extend(pids)
            elif pids:
                all_pids.append(pids)

            if data.get("title_with_lang"):
                for title_item in data["title_with_lang"]:
                    lang = title_item.get("language", "en")
                    text = title_item.get("text", "")
                    if text:
                        all_titles[lang] = text

            if data.get("abstract_with_lang"):
                for abstract_item in data["abstract_with_lang"]:
                    lang = abstract_item.get("language", "en")
                    text = abstract_item.get("text", "")
                    if text:
                        all_abstracts[lang] = text

            if data.get("keywords_with_lang"):
                for keyword_item in data["keywords_with_lang"]:
                    lang = keyword_item.get("language", "en")
                    keywords = keyword_item.get("keywords", [])
                    if keywords:
                        all_keywords[lang] = list(
                            set(all_keywords.get(lang, []) + keywords)
                        )

            if data.get("content_url_with_lang"):
                all_urls.extend(data["content_url_with_lang"])

        base_data.setdefault("oca_data", {}).setdefault("scielo", {})
        base_data["oca_data"]["scielo"]["collection"] = scalar_or_list(
            unique(all_collections)
        )
        base_data["oca_data"]["scielo"]["ids"] = unique(all_pids)
        base_data["oca_data"]["scielo"]["pid_v2"] = scalar_or_list(unique(all_pids))

        if all_titles:
            base_data["title_with_lang"] = [
                {"language": lang, "text": text}
                for lang, text in sorted(all_titles.items())
            ]
        if all_abstracts:
            base_data["abstract_with_lang"] = [
                {"language": lang, "text": text}
                for lang, text in sorted(all_abstracts.items())
            ]
        if all_keywords:
            base_data["keywords_with_lang"] = [
                {"language": lang, "keywords": keywords}
                for lang, keywords in sorted(all_keywords.items())
            ]
        if all_urls:
            base_data["content_url_with_lang"] = self._unique_urls_by_language(all_urls)

        try:
            return SilverDocument(**base_data)
        except Exception as exc:
            logger.error("Failed to consolidate SciELO group: %s", exc)
            return scielo_docs[0]

    def _unique_urls_by_language(self, url_items: list) -> list:
        seen_langs = set()
        unique_urls = []
        for url_item in url_items:
            if not isinstance(url_item, dict):
                continue
            lang = url_item.get("language")
            if lang and lang not in seen_langs:
                unique_urls.append(url_item)
                seen_langs.add(lang)
            elif not lang:
                unique_urls.append(url_item)
        return unique_urls

    def _enrich_scielo_with_openalex(
        self,
        base_scielo: SilverDocument,
        openalex_docs: list[SilverDocument],
    ) -> SilverDocument:
        if not openalex_docs:
            return base_scielo

        logger.debug("Enriching with %s OpenAlex document(s)", len(openalex_docs))

        merged_data = base_scielo.to_dict()
        all_citation_counts = []
        all_referenced_works = []
        all_authorships = []
        all_country_codes = set()
        all_institutions = []
        all_metrics = {}
        all_sdgs = []
        all_indexed_in = list(merged_data.get("indexed_in") or [])
        openalex_doi = None
        openalex_doi_with_lang = []
        all_funders = []
        all_awards = []
        best_primary_topic_score = merged_data.get("primary_topic_score") or 0.0
        merged_apc = merged_data.get("apc") or {}

        for oa_doc in openalex_docs:
            oa_data = oa_doc.to_dict()
            oa_ids = oa_data.get("ids") or {}
            if not openalex_doi:
                openalex_doi = oa_data.get("doi") or oa_ids.get("doi")
            if oa_ids.get("doi_with_lang"):
                openalex_doi_with_lang.extend(oa_ids["doi_with_lang"])
            if oa_data.get("citation_count") is not None:
                all_citation_counts.append(oa_data["citation_count"])
            if oa_data.get("referenced_works"):
                all_referenced_works.extend(oa_data["referenced_works"])
            if oa_data.get("authorships"):
                all_authorships.extend(oa_data["authorships"])
            if oa_data.get("author_country_codes"):
                all_country_codes.update(oa_data["author_country_codes"])
            if oa_data.get("institutions"):
                all_institutions.extend(oa_data["institutions"])
            if oa_data.get("metrics"):
                all_metrics.update(oa_data["metrics"])
            if oa_data.get("sustainable_development_goals"):
                all_sdgs.extend(oa_data["sustainable_development_goals"])
            if oa_data.get("indexed_in"):
                all_indexed_in.extend(as_list(oa_data["indexed_in"]))
            if oa_data.get("funders"):
                all_funders.extend(oa_data["funders"])
            if oa_data.get("awards"):
                all_awards.extend(oa_data["awards"])
            if oa_data.get("primary_topic_name") and oa_data.get("primary_topic_score"):
                oa_score = float(oa_data["primary_topic_score"])
                if oa_score > best_primary_topic_score:
                    best_primary_topic_score = oa_score
                    merged_data["primary_topic_name"] = oa_data["primary_topic_name"]
                    merged_data["primary_topic_domain"] = oa_data["primary_topic_domain"]
                    merged_data["primary_topic_field"] = oa_data["primary_topic_field"]
                    merged_data["primary_topic_subfield"] = oa_data["primary_topic_subfield"]
                    merged_data["primary_topic_score"] = oa_data["primary_topic_score"]
            if not merged_apc and oa_data.get("apc"):
                merged_apc = oa_data["apc"]

        if merged_data.get("citation_count") is not None:
            all_citation_counts.insert(0, merged_data["citation_count"])
        if all_citation_counts:
            merged_data["citation_count"] = sum(all_citation_counts)
        if all_referenced_works:
            merged_data["referenced_works"] = unique(
                (merged_data.get("referenced_works") or []) + all_referenced_works
            )
        merged_data["references_count"] = len(merged_data.get("referenced_works") or [])

        scielo_authorships = merged_data.get("authorships", [])
        if scielo_authorships and all_authorships:
            merged_data["authorships"] = self._merge_authorships(
                scielo_authorships,
                all_authorships,
            )
        elif all_authorships and not scielo_authorships:
            merged_data["authorships"] = all_authorships

        sc_countries = set(merged_data.get("author_country_codes", []))
        merged_data["author_country_codes"] = sorted(sc_countries | all_country_codes)

        if all_institutions:
            existing_insts = merged_data.get("institutions") or []
            merged_data["institutions"] = list(dict.fromkeys(existing_insts + all_institutions))

        if all_metrics:
            merged_data["metrics"] = {**(merged_data.get("metrics") or {}), **all_metrics}
        if all_sdgs:
            merged_data["sustainable_development_goals"] = self._unique_sdgs_by_score(
                (merged_data.get("sustainable_development_goals") or []) + all_sdgs
            )
        if all_funders:
            existing_funders = merged_data.get("funders") or []
            merged_data["funders"] = self._unique_funders(existing_funders + all_funders)
        if all_awards:
            existing_awards = merged_data.get("awards") or []
            merged_data["awards"] = self._unique_awards(existing_awards + all_awards)
        if merged_apc:
            merged_data["apc"] = merged_apc
        if all_indexed_in:
            merged_data["indexed_in"] = sorted(set(all_indexed_in))
        if openalex_doi and not merged_data.get("doi"):
            merged_data["doi"] = openalex_doi
            merged_data.setdefault("ids", {}).setdefault("doi", openalex_doi)
        if openalex_doi_with_lang:
            merged_ids = merged_data.setdefault("ids", {})
            if not merged_ids.get("doi_with_lang"):
                merged_ids["doi_with_lang"] = openalex_doi_with_lang

        all_languages = set(as_list(merged_data.get("language") or []))
        for item in merged_data.get("title_with_lang") or []:
            if (lang := item.get("language")) and (
                normalized := normalize_language(lang)
            ):
                all_languages.add(normalized)
        for oa_doc in openalex_docs:
            for item in (oa_doc.to_dict().get("title_with_lang") or []):
                if (lang := item.get("language")) and (
                    normalized := normalize_language(lang)
                ):
                    all_languages.add(normalized)
        if all_languages:
            merged_data["language"] = sorted(all_languages)

        if openalex_docs:
            oa_source = openalex_docs[0].source or {}
            if oa_source:
                sc_source = merged_data.get("source") or {}
                if oa_source.get("id"):
                    sc_source.setdefault("ids", {})["openalex"] = oa_source["id"]
                for key in ("title", "issn_l", "host_organization", "host_organization_name", "type"):
                    if not sc_source.get(key) and oa_source.get(key):
                        sc_source[key] = oa_source[key]

                oa_issns = as_list(oa_source.get("issns"))
                sc_issns = as_list(sc_source.get("issns"))
                sc_source["issns"] = unique(sc_issns + oa_issns)

                merged_data["source"] = sc_source
                merged_data["source_title"] = sc_source.get("title")
                merged_data["source_issns"] = sc_source.get("issns") or []
                merged_data["source_type"] = sc_source.get("type")

        try:
            return SilverDocument(**merged_data)
        except Exception as exc:
            logger.error("Failed to enrich with OpenAlex docs: %s", exc)
            return base_scielo

    def _unique_funders(self, funders: list) -> list:
        seen_ids = set()
        seen_rors = set()
        seen_names = set()
        unique_funders = []
        for funder in funders:
            if not isinstance(funder, dict):
                continue
            funder_id = funder.get("id")
            ror = funder.get("ror")
            name = normalize_author_name(funder.get("name", ""))
            if (funder_id and funder_id in seen_ids) or (ror and ror in seen_rors) or (name and name in seen_names):
                continue
            unique_funders.append(funder)
            if funder_id:
                seen_ids.add(funder_id)
            if ror:
                seen_rors.add(ror)
            if name:
                seen_names.add(name)
        return unique_funders

    def _unique_awards(self, awards: list) -> list:
        seen_award_ids = set()
        unique_awards = []
        for award in awards:
            if not isinstance(award, dict):
                continue
            award_id = award.get("award_id") or award.get("id")
            if award_id and award_id in seen_award_ids:
                continue
            unique_awards.append(award)
            if award_id:
                seen_award_ids.add(award_id)
        return unique_awards

    def _unique_sdgs_by_score(self, sdgs: list) -> list:
        sdgs_by_id = {}

        for sdg in sdgs:
            sdg_id = sdg["id"]
            current = sdgs_by_id.get(sdg_id)
            if current is None or (sdg.get("score") or 0) > (current.get("score") or 0):
                sdgs_by_id[sdg_id] = sdg

        return list(sdgs_by_id.values())

    def _with_merge_trace(
        self,
        merged_doc: SilverDocument,
        scielo_docs: list[SilverDocument],
        openalex_matches: list[tuple[SilverDocument, str, float, dict]],
    ) -> SilverDocument:
        data = merged_doc.to_dict()
        data.setdefault("ids", {})
        data.setdefault("oca_data", {})

        scielo_ids = [str(x) for x in unique(
            [item for doc in scielo_docs for item in self._scielo_ids(doc)]
        )]
        scielo_collections = [str(x) for x in unique(
            [item for doc in scielo_docs for item in self._scielo_collections(doc)]
        )]

        openalex_ids = []
        openalex_match_details = []
        openalex_lang_map: dict[str, list[str]] = {}
        for oa_doc, strategy, confidence, validation in openalex_matches:
            oa_id_list = self._openalex_ids(oa_doc)
            if oa_id_list:
                openalex_ids.extend(oa_id_list)
                oa_langs = as_list(oa_doc.language or [])
                for oa_id in oa_id_list:
                    openalex_lang_map.setdefault(oa_id, []).extend(oa_langs)
            openalex_match_details.append(
                {
                    "doc_id": oa_id_list[0] if oa_id_list else None,
                    "match_strategy": strategy,
                    "confidence": confidence,
                    "validation": validation,
                }
            )

        openalex_ids = unique(openalex_ids)

        if scielo_ids:
            data["ids"]["scielo"] = scalar_or_list(scielo_ids)
            scielo = dict(data["oca_data"].get("scielo") or {})
            scielo["ids"] = scielo_ids
            scielo["pid_v2"] = scalar_or_list(scielo_ids)
            if scielo_collections:
                scielo["collection"] = scalar_or_list(scielo_collections)
            data["oca_data"]["scielo"] = scielo

        if openalex_ids:
            data["ids"]["openalex"] = scalar_or_list(openalex_ids)
            data["openalex_id"] = openalex_ids[0]

            oa_lang_items = []
            for oa_id in openalex_ids:
                for lang in openalex_lang_map.get(oa_id) or []:
                    oa_lang_items.append({"language": lang, "openalex": oa_id})
            if oa_lang_items:
                data["ids"]["openalex_with_lang"] = oa_lang_items

            openalex = dict(data["oca_data"].get("openalex") or {})
            openalex["ids"] = openalex_ids
            data["oca_data"]["openalex"] = openalex

        data["oca_data"]["merge_trace"] = {
            "scielo_matches": {
                "doc_ids": scielo_ids,
                "collections": scielo_collections,
            },
            "openalex_matches": openalex_match_details,
        }
        data["oca_data"]["scope"] = (
            ["scielo", "openalex"] if openalex_matches else ["scielo"]
        )

        return SilverDocument(**data)
