import re

from etl.transform.normalizers import normalize_country_code, normalize_issn
from search_gateway.option_normalization import clean_text, normalize_boolean


def global_metric_row_from_hit(hit):
    source = hit.get("_source") or {}
    raw_data = source.get("raw_data") or {}
    if not isinstance(raw_data, dict):
        return None

    issns = issn_terms(raw_data.get("issns"))
    year = coerce_int(raw_data.get("year"))
    if not issns or year is None:
        return None

    indexed_in = []
    if normalize_boolean(raw_data.get("scopus_active_in_the_year")):
        indexed_in.append("Scopus")
    if normalize_boolean(raw_data.get("wos_active_in_the_year")):
        indexed_in.append("WoS")
    if normalize_boolean(raw_data.get("scielo_active_and_valid_in_the_year")):
        indexed_in.append("SciELO")

    country = clean_text(raw_data.get("country"))
    country_code = normalize_country_code(country)
    if not indexed_in and not country_code:
        return None

    return {
        "issns": issns,
        "year": year,
        "indexed_in": indexed_in,
        "country": country,
        "country_code": country_code,
    }


def issns_overlap(first, second):
    first_values = {normalize_issn(value) or clean_text(value) for value in first}
    second_values = {normalize_issn(value) or clean_text(value) for value in second}
    first_values.discard("")
    second_values.discard("")
    return bool(first_values & second_values)


def issn_terms(value):
    terms = []
    for item in as_values(value):
        raw_value = clean_text(item)
        if not raw_value:
            continue
        append_unique(terms, raw_value)
        append_unique(terms, normalize_issn(raw_value))
    return terms


def as_values(value):
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return list(value)
    if isinstance(value, str):
        return [item for item in re.split(r"[,;|]", value) if item.strip()]
    return [value]


def coerce_int(value):
    if value in (None, ""):
        return None
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return None


def append_unique(values, value):
    if value and value not in values:
        values.append(value)
