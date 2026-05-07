from typing import Any

from etl.normalizers import stz_doi, stz_isbn, stz_issn


def extract_doi(doc: dict[str, Any]) -> str | None:
    if doi := doc.get("doi"):
        return doi

    ids = doc.get("ids") if isinstance(doc.get("ids"), dict) else {}
    if ids.get("doi"):
        return ids["doi"]

    for items in (ids.get("doi_with_lang"), doc.get("doi_with_lang")):
        for item in items or []:
            if isinstance(item, dict):
                return item.get("doi") or item.get("id") or item.get("value")
            if item:
                return item

    return None


def extract_isbns(doc: dict[str, Any]) -> list[str]:
    values: list[str] = []
    ids = doc.get("ids") if isinstance(doc.get("ids"), dict) else {}
    biblio = doc.get("biblio") if isinstance(doc.get("biblio"), dict) else {}

    for key in ("isbn", "eisbn", "isbns", "eisbns"):
        raw_value = doc.get(key) or ids.get(key) or biblio.get(key)
        if isinstance(raw_value, list):
            values.extend(raw_value)
        elif raw_value:
            values.append(raw_value)

    parent = doc.get("parent_book") if isinstance(doc.get("parent_book"), dict) else {}
    parent_ids = parent.get("ids") if isinstance(parent.get("ids"), dict) else {}
    for key in ("isbn", "eisbn", "isbns", "eisbns"):
        raw_value = parent_ids.get(key)
        if isinstance(raw_value, list):
            values.extend(raw_value)
        elif raw_value:
            values.append(raw_value)

    for location_key in ("primary_location", "best_oa_location"):
        location = doc.get(location_key) if isinstance(doc.get(location_key), dict) else {}
        source = location.get("source") if isinstance(location.get("source"), dict) else {}
        raw_value = source.get("issns") or source.get("issn")
        if isinstance(raw_value, list):
            values.extend(raw_value)
        elif raw_value:
            values.append(raw_value)

    for location in doc.get("locations") or []:
        if not isinstance(location, dict):
            continue
        source = location.get("source") if isinstance(location.get("source"), dict) else {}
        raw_value = source.get("issns") or source.get("issn")
        if isinstance(raw_value, list):
            values.extend(raw_value)
        elif raw_value:
            values.append(raw_value)

    return sorted({normalized for value in values if (normalized := stz_isbn(value))})


def extract_issns(doc: dict[str, Any]) -> list[str]:
    issns: set[str] = set()

    for field in ("source_issns", "journal_issns"):
        raw_value = doc.get(field)
        if isinstance(raw_value, list):
            issns.update(raw_value)

    source = doc.get("source")
    if isinstance(source, dict):
        for field in ("issns", "issn"):
            raw_value = source.get(field)
            if isinstance(raw_value, list):
                issns.update(raw_value)
            elif isinstance(raw_value, str):
                issns.add(raw_value)

    sources = doc.get("sources")
    if isinstance(sources, list):
        for source_item in sources:
            if not isinstance(source_item, dict):
                continue
            for field in ("issn", "issns"):
                raw_value = source_item.get(field)
                if isinstance(raw_value, list):
                    issns.update(raw_value)
                elif isinstance(raw_value, str):
                    issns.add(raw_value)

    for location_key in ("primary_location", "best_oa_location"):
        location = doc.get(location_key)
        if not isinstance(location, dict):
            continue
        source_item = location.get("source")
        if not isinstance(source_item, dict):
            continue
        for field in ("issns", "issn"):
            raw_value = source_item.get(field)
            if isinstance(raw_value, list):
                issns.update(raw_value)
            elif isinstance(raw_value, str):
                issns.add(raw_value)

    return sorted({normalized for value in issns if (normalized := stz_issn(value))})


def extract_scielo_id(doc: dict[str, Any]) -> str | None:
    if scielo_id := doc.get("scielo_id"):
        return scielo_id
    if pid_v2 := doc.get("pid_v2"):
        return pid_v2
    if code := doc.get("code"):
        return code

    ids = doc.get("ids") if isinstance(doc.get("ids"), dict) else {}
    return ids.get("scl_preprint_id")


def normalize_identifiers(raw_doc: dict[str, Any]) -> dict[str, str | None]:
    identifiers: dict[str, str | None] = {}

    if doi := extract_doi(raw_doc):
        if normalized_doi := stz_doi(doi):
            identifiers["doi"] = normalized_doi

    ids = raw_doc.get("ids") if isinstance(raw_doc.get("ids"), dict) else {}

    if issn := raw_doc.get("issn") or ids.get("issn"):
        issn_values = issn if isinstance(issn, list) else [issn]
        if normalized_issn := next(
            (stz_issn(value) for value in issn_values if stz_issn(value)),
            None,
        ):
            identifiers["issn"] = normalized_issn

    if isbn := raw_doc.get("isbn") or ids.get("isbn") or ids.get("eisbn"):
        isbn_values = isbn if isinstance(isbn, list) else [isbn]
        if normalized_isbn := next(
            (stz_isbn(value) for value in isbn_values if stz_isbn(value)),
            None,
        ):
            identifiers["isbn"] = normalized_isbn

    if openalex_id := raw_doc.get("openalex_id") or raw_doc.get("id"):
        identifiers["openalex_id"] = str(openalex_id).strip()

    if pid := raw_doc.get("pid_v2") or raw_doc.get("scielo_id"):
        identifiers["scielo_id"] = str(pid).strip()

    for key in ("pmid", "pmcid", "mag"):
        if value := raw_doc.get(key):
            identifiers[key] = str(value).strip()

    return identifiers
