import logging

from etl.documents import SilverDocument
from etl.transform.normalizers import as_list, normalize_name, scalar_or_list, unique
from etl.pipeline.defaults import DocumentRules

logger = logging.getLogger(__name__)


def _authors_match(sc_author: dict, oa_author: dict) -> bool:
    sc_name = normalize_name(sc_author.get("name", ""))
    oa_name = normalize_name(oa_author.get("name", ""))
    if sc_name and oa_name and sc_name == oa_name:
        return True

    sc_orcid = sc_author.get("orcid")
    oa_orcid = oa_author.get("orcid")
    if sc_orcid and oa_orcid and sc_orcid == oa_orcid:
        return True

    sc_id = sc_author.get("id")
    oa_id = oa_author.get("id")
    if sc_id and oa_id and sc_id == oa_id:
        return True

    return False


def _merge_author_institutions(sc_institutions: list, oa_institutions: list) -> list:
    if not oa_institutions:
        return list(sc_institutions)

    existing_ids = {inst.get("id") for inst in sc_institutions if isinstance(inst, dict) and inst.get("id")}
    existing_rors = {inst.get("ror") for inst in sc_institutions if isinstance(inst, dict) and inst.get("ror")}
    existing_names = {
        normalize_name(inst.get("name", ""))
        for inst in sc_institutions
        if isinstance(inst, dict) and inst.get("name")
    }

    merged = list(sc_institutions)
    for oa_inst in oa_institutions:
        if not isinstance(oa_inst, dict):
            continue

        inst_id = oa_inst.get("id")
        ror = oa_inst.get("ror")
        oa_name = normalize_name(oa_inst.get("name", ""))
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


def _enrich_authorships(scielo_authorships: list, openalex_authorships: list) -> list:
    enriched = []
    matched_oa_indices = set()

    for sc_author in scielo_authorships:
        enriched_author = dict(sc_author)

        best_match = None
        best_match_idx = None
        for idx, oa_author in enumerate(openalex_authorships):
            if idx in matched_oa_indices:
                continue
            if _authors_match(sc_author, oa_author):
                best_match = oa_author
                best_match_idx = idx
                break

        if best_match:
            matched_oa_indices.add(best_match_idx)
            if not enriched_author.get("id") and best_match.get("id"):
                enriched_author["id"] = best_match["id"]
            if not enriched_author.get("orcid") and best_match.get("orcid"):
                enriched_author["orcid"] = best_match["orcid"]
            enriched_author["institutions"] = _merge_author_institutions(
                enriched_author.get("institutions", []),
                best_match.get("institutions", []),
            )

        enriched.append(enriched_author)

    for idx, oa_author in enumerate(openalex_authorships):
        if idx not in matched_oa_indices:
            if not any(_authors_match(enr_author, oa_author) for enr_author in enriched):
                enriched.append(dict(oa_author))

    return enriched


def _enrich_institutions(scielo_institutions: list, openalex_institutions: list) -> list:
    scielo_ids = set()
    scielo_rors = set()
    scielo_names = set()

    for inst in scielo_institutions:
        if isinstance(inst, dict):
            if inst.get("id"):
                scielo_ids.add(inst["id"])
            if inst.get("ror"):
                scielo_rors.add(inst["ror"])
            name = normalize_name(inst.get("name", ""))
            if name:
                scielo_names.add(name)

    merged = list(scielo_institutions)

    for oa_inst in openalex_institutions:
        if not isinstance(oa_inst, dict):
            continue

        inst_id = oa_inst.get("id")
        ror = oa_inst.get("ror")
        oa_name = normalize_name(oa_inst.get("name", ""))

        if inst_id and inst_id in scielo_ids:
            continue
        if ror and ror in scielo_rors:
            continue
        if oa_name and oa_name in scielo_names:
            continue

        merged.append(oa_inst)
        if inst_id:
            scielo_ids.add(inst_id)
        if ror:
            scielo_rors.add(ror)
        if oa_name:
            scielo_names.add(oa_name)

    return merged


def _collect_openalex_ids(doc: SilverDocument) -> list:
    ids = []
    if doc.openalex_id:
        ids.append(doc.openalex_id)

    indexed_ids = doc.ids or {}
    ids.extend(as_list(indexed_ids.get("openalex")))

    openalex = (doc.oca_data or {}).get("openalex") or {}
    ids.extend(as_list(openalex.get("ids")))

    return unique([value for value in ids if isinstance(value, str) and "openalex.org/W" in value])


def _collect_scielo_ids(doc: SilverDocument) -> list:
    ids = []
    if doc.scielo_id:
        ids.append(doc.scielo_id)

    indexed_ids = doc.ids or {}
    ids.extend(as_list(indexed_ids.get("scielo")))

    scielo = (doc.oca_data or {}).get("scielo") or {}
    ids.extend(as_list(scielo.get("ids")))
    ids.extend(as_list(scielo.get("pid_v2")))

    return unique(ids)


def _collect_scielo_collections(doc: SilverDocument) -> list:
    scielo = (doc.oca_data or {}).get("scielo") or {}
    return unique(as_list(scielo.get("collection")))


def _consolidate_scielo_group(scielo_docs: list[SilverDocument]) -> SilverDocument:
    if len(scielo_docs) == 1:
        return scielo_docs[0]

    logger.debug(f"Consolidating {len(scielo_docs)} SciELO duplicates")

    base_data = scielo_docs[0].to_dict()

    all_collections = []
    all_pids = []
    all_titles = {}
    all_abstracts = {}
    all_keywords = {}
    all_urls = []

    for doc in scielo_docs:
        data = doc.to_dict()
        oca_data = data.get("oca_data", {})
        scielo_info = oca_data.get("scielo", {})

        if scielo_info.get("collection"):
            colls = (
                scielo_info["collection"]
                if isinstance(scielo_info["collection"], list)
                else [scielo_info["collection"]]
            )
            all_collections.extend(colls)

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
            for abs_item in data["abstract_with_lang"]:
                lang = abs_item.get("language", "en")
                text = abs_item.get("text", "")
                if text:
                    all_abstracts[lang] = text

        if data.get("keywords_with_lang"):
            for kw_item in data["keywords_with_lang"]:
                lang = kw_item.get("language", "en")
                keywords = kw_item.get("keywords", [])
                if keywords:
                    all_keywords[lang] = list(set(all_keywords.get(lang, []) + keywords))

        if data.get("content_url_with_lang"):
            all_urls.extend(data["content_url_with_lang"])

    base_data.setdefault("oca_data", {}).setdefault("scielo", {})
    base_data["oca_data"]["scielo"]["collection"] = scalar_or_list(unique(all_collections))
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
            {"language": lang, "keywords": kws}
            for lang, kws in sorted(all_keywords.items())
        ]

    if all_urls:
        seen_langs = set()
        unique_urls = []
        for url_item in all_urls:
            if isinstance(url_item, dict):
                lang = url_item.get("language")
                if lang and lang not in seen_langs:
                    unique_urls.append(url_item)
                    seen_langs.add(lang)
                elif not lang:
                    unique_urls.append(url_item)
        base_data["content_url_with_lang"] = unique_urls

    try:
        return SilverDocument(**base_data)
    except Exception as e:
        logger.error(f"Failed to consolidate SciELO group: {e}")
        return scielo_docs[0]


def _enrich_with_openalex(
    base_scielo: SilverDocument,
    openalex_docs: list[SilverDocument],
    rules: DocumentRules,
) -> SilverDocument:
    if not openalex_docs:
        return base_scielo

    if not rules.merge.scielo_is_base:
        raise ValueError(f"Merge rules for {rules.document_type} must keep SciELO as base")

    logger.debug(f"Enriching with {len(openalex_docs)} OpenAlex document(s)")
    actions = rules.merge.field_actions

    merged_data = base_scielo.to_dict()

    all_citation_counts = []
    all_topics = []
    all_referenced_works = []
    all_authorships = []
    all_institutions = []
    all_country_codes = set()
    all_metrics = {}

    for oa_doc in openalex_docs:
        oa_data = oa_doc.to_dict()

        if oa_data.get("citation_count") is not None:
            all_citation_counts.append(oa_data["citation_count"])

        if oa_data.get("topics"):
            all_topics.extend(oa_data["topics"])
        elif oa_data.get("topic"):
            all_topics.append(oa_data["topic"])

        if oa_data.get("referenced_works"):
            all_referenced_works.extend(oa_data["referenced_works"])

        if oa_data.get("authorships"):
            all_authorships.extend(oa_data["authorships"])

        if oa_data.get("institutions"):
            all_institutions.extend(oa_data["institutions"])

        if oa_data.get("author_country_codes"):
            all_country_codes.update(oa_data["author_country_codes"])

        if oa_data.get("metrics"):
            all_metrics.update(oa_data["metrics"])

    if actions.get("citation_count") == "sum" and all_citation_counts:
        merged_data["citation_count"] = sum(all_citation_counts)
    elif actions.get("citation_count") == "max" and all_citation_counts:
        merged_data["citation_count"] = max(all_citation_counts)

    if actions.get("topics") == "openalex_if_missing" and all_topics and not merged_data.get("topics"):
        seen_topics = set()
        unique_topics = []
        for topic in all_topics:
            topic_id = topic.get("id") if isinstance(topic, dict) else str(topic)
            if topic_id and topic_id not in seen_topics:
                unique_topics.append(topic)
                seen_topics.add(topic_id)
        merged_data["topics"] = unique_topics

    if actions.get("referenced_works") == "union" and all_referenced_works:
        merged_data["referenced_works"] = unique(all_referenced_works)

    scielo_authorships = merged_data.get("authorships", [])
    if actions.get("authorships") == "prefer_scielo" and scielo_authorships and all_authorships:
        merged_data["authorships"] = _enrich_authorships(scielo_authorships, all_authorships)
    elif actions.get("authorships") == "prefer_scielo" and all_authorships and not scielo_authorships:
        merged_data["authorships"] = all_authorships

    scielo_institutions = merged_data.get("institutions", [])
    if actions.get("institutions") == "prefer_scielo" and scielo_institutions and all_institutions:
        merged_data["institutions"] = _enrich_institutions(scielo_institutions, all_institutions)
    elif actions.get("institutions") == "prefer_scielo" and all_institutions and not scielo_institutions:
        seen_ids = set()
        unique_insts = []
        for inst in all_institutions:
            inst_id = inst.get("id")
            if inst_id and inst_id not in seen_ids:
                unique_insts.append(inst)
                seen_ids.add(inst_id)
            elif not inst_id:
                unique_insts.append(inst)
        merged_data["institutions"] = unique_insts

    if actions.get("author_country_codes") == "union":
        sc_countries = set(merged_data.get("author_country_codes", []))
        merged_data["author_country_codes"] = sorted(sc_countries | all_country_codes)

    if actions.get("metrics") == "union" and all_metrics:
        merged_data["metrics"] = {**(merged_data.get("metrics") or {}), **all_metrics}

    try:
        return SilverDocument(**merged_data)
    except Exception as e:
        logger.error(f"Failed to enrich with OpenAlex docs: {e}")
        return base_scielo


def _add_merge_trace(
    merged_doc: SilverDocument,
    scielo_docs: list[SilverDocument],
    openalex_matches: list[tuple[SilverDocument, str, float, dict]],
) -> SilverDocument:
    data = merged_doc.to_dict()
    data.setdefault("ids", {})
    data.setdefault("oca_data", {})

    scielo_ids = unique([item for doc in scielo_docs for item in _collect_scielo_ids(doc)])
    scielo_collections = unique([item for doc in scielo_docs for item in _collect_scielo_collections(doc)])

    openalex_ids = []
    openalex_match_details = []

    for oa_doc, strategy, confidence, validation in openalex_matches:
        oa_id_list = _collect_openalex_ids(oa_doc)
        if oa_id_list:
            openalex_ids.extend(oa_id_list)
        openalex_match_details.append({
            "doc_id": oa_id_list[0] if oa_id_list else None,
            "match_strategy": strategy,
            "confidence": confidence,
            "validation": validation,
        })

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
        openalex = dict(data["oca_data"].get("openalex") or {})
        openalex["ids"] = openalex_ids
        data["oca_data"]["openalex"] = openalex

    data["oca_data"]["merge_trace"] = {
        "merged": True,
        "scielo_group": {
            "doc_ids": scielo_ids,
            "collections": scielo_collections,
            "total_duplicates": len(scielo_docs),
        },
        "openalex_matches": openalex_match_details,
        "rejected_matches": [],
    }

    data["oca_data"]["merged"] = True
    data["oca_data"]["scope"] = ["scielo", "openalex"] if openalex_matches else ["scielo"]

    return SilverDocument(**data)


def merge(
    scielo_docs: list[SilverDocument],
    openalex_matches: list[tuple[SilverDocument, str, float, dict]],
    rules: DocumentRules,
) -> SilverDocument:
    if not scielo_docs:
        raise ValueError("At least one SciELO document is required")

    if rules.document_type != scielo_docs[0].type:
        raise ValueError(
            f"Merge rules type {rules.document_type} does not match SciELO document type {scielo_docs[0].type}"
        )

    logger.info(
        f"Merging {len(scielo_docs)} SciELO doc(s) with "
        f"{len(openalex_matches)} OpenAlex match(es)"
    )

    base_scielo = _consolidate_scielo_group(scielo_docs)
    openalex_docs = [match[0] for match in openalex_matches]

    if openalex_docs:
        merged = _enrich_with_openalex(base_scielo, openalex_docs, rules)
    else:
        merged = base_scielo
        merged.oca_data.setdefault("scope", []).append("scielo")
        merged.oca_data["merged"] = True

    return _add_merge_trace(merged, scielo_docs, openalex_matches)
