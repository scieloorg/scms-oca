import re
from typing import Any

from etl.transform.normalizers import (
    normalize_doi,
    normalize_isbn,
    normalize_issn,
    normalize_text,
)


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

    return sorted({normalized for value in values if (normalized := normalize_isbn(value))})


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

    return sorted({normalized for value in issns if (normalized := normalize_issn(value))})


def extract_scielo_id(doc: dict[str, Any]) -> str | None:
    if scielo_id := doc.get("scielo_id"):
        return scielo_id
    if pid_v2 := doc.get("pid_v2"):
        return pid_v2
    if code := doc.get("code"):
        return code

    ids = doc.get("ids") if isinstance(doc.get("ids"), dict) else {}
    return ids.get("scl_preprint_id")


def extract_scielo_document_type(doc):
    raw_document_type = doc.get("document_type") or doc.get("type")
    if not raw_document_type:
        return None

    return str(raw_document_type).strip().lower().replace("_", "-")


def extract_identifiers(raw_doc: dict[str, Any]) -> dict[str, str | None]:
    identifiers: dict[str, str | None] = {}

    if doi := extract_doi(raw_doc):
        if normalized_doi := normalize_doi(doi):
            identifiers["doi"] = normalized_doi

    ids = raw_doc.get("ids") if isinstance(raw_doc.get("ids"), dict) else {}

    if issn := raw_doc.get("issn") or ids.get("issn"):
        issn_values = issn if isinstance(issn, list) else [issn]
        if normalized_issn := next(
            (normalize_issn(value) for value in issn_values if normalize_issn(value)),
            None,
        ):
            identifiers["issn"] = normalized_issn

    if isbn := raw_doc.get("isbn") or ids.get("isbn") or ids.get("eisbn"):
        isbn_values = isbn if isinstance(isbn, list) else [isbn]
        if normalized_isbn := next(
            (normalize_isbn(value) for value in isbn_values if normalize_isbn(value)),
            None,
        ):
            identifiers["isbn"] = normalized_isbn

    if pid := raw_doc.get("pid_v2") or raw_doc.get("scielo_id"):
        identifiers["scielo_id"] = str(pid).strip()

    for key in ("pmid", "pmcid", "mag"):
        if value := raw_doc.get(key):
            identifiers[key] = str(value).strip()

    return identifiers


def extract_source(doc: dict[str, Any]) -> dict[str, Any]:
    source = doc.get("source")
    if isinstance(source, dict) and source:
        return source

    for location_key in ("primary_location", "best_oa_location"):
        location = doc.get(location_key)
        if isinstance(location, dict):
            location_source = location.get("source")
            if isinstance(location_source, dict):
                return location_source

    return {}


def extract_titles(doc: dict[str, Any]) -> list[str]:
    titles: list[str] = []

    for entry in doc.get("title_with_lang", []):
        if isinstance(entry, dict) and entry.get("title"):
            normalized = normalize_text(entry["title"])
            if normalized:
                titles.append(normalized.lower().strip())

    if not titles:
        title = doc.get("title") or doc.get("display_name", "")
        if title:
            normalized = normalize_text(title)
            if normalized:
                titles.append(normalized.lower().strip())

    return titles


def extract_abstract_from_inverted_index(inverted_index: dict) -> str | None:
    if not inverted_index or not isinstance(inverted_index, dict):
        return None

    word_positions = []
    for word, positions in inverted_index.items():
        for position in positions:
            word_positions.append((position, word))
    word_positions.sort()
    abstract = " ".join(word for _position, word in word_positions)
    return normalize_text(abstract)


def extract_display_name(value: Any) -> Any:
    if isinstance(value, dict):
        return value.get("display_name") or value.get("name")
    return value


def extract_publication_year(raw_data: dict[str, Any]) -> int | None:
    for field in ("publication_year", "year", "pub_year"):
        val = raw_data.get(field)
        if val:
            try:
                year = int(float(val))
                if 1000 < year < 2100:
                    return year
            except (ValueError, TypeError):
                pass

    monograph = raw_data.get("monograph")
    if isinstance(monograph, dict):
        year = extract_publication_year(monograph)
        if year:
            return year

        monograph_pub_date = monograph.get("publication_date")
        if monograph_pub_date and isinstance(monograph_pub_date, str):
            match = re.search(r"(\d{4})", monograph_pub_date)
            if match:
                try:
                    year = int(match.group(1))
                    if 1000 < year < 2100:
                        return year
                except (ValueError, TypeError):
                    pass

    for field in (
        "publication_date",
        "pub_date",
        "date",
        "release_time",
        "create_time",
        "citation_date",
    ):
        val = raw_data.get(field)
        if val and isinstance(val, str):
            match = re.search(r"(\d{4})", val)
            if match:
                try:
                    year = int(match.group(1))
                    if 1000 < year < 2100:
                        return year
                except (ValueError, TypeError):
                    pass

    return None
