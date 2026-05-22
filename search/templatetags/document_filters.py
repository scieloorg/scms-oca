from django import template

from harvest.language_normalizer import normalize_language_field
from search.normalize import (
    as_list,
    deduplicate_variants_by_value,
    orcid_url as build_orcid_url,
    split_lang_code,
    unique,
)


register = template.Library()


def _language_codes_from_translations(source):
    codes = []
    explicit = set(_normalize_language_codes(source.get("language")))

    for key, value in source.items():
        if not str(key).endswith("_with_lang") or not isinstance(value, list):
            continue

        value_key = str(key)[: -len("_with_lang")]
        variants = []

        for item in value:
            if not isinstance(item, dict):
                continue

            raw_value = item.get(value_key)
            if raw_value in (None, "", []):
                continue

            for code in as_list(normalize_language_field(item.get("language"))):
                _, base = split_lang_code(code)
                if not base:
                    continue

                variants.append({"language": base, "value": raw_value})

        for variant in deduplicate_variants_by_value(
            variants,
            explicit_languages=explicit,
        ):
            base = variant["language"]
            if base not in codes:
                codes.append(base)

    return codes


def _normalize_language_codes(value):
    codes = []
    for code in as_list(normalize_language_field(value)):
        _, base = split_lang_code(code)
        if base:
            codes.append(base)
    return unique(codes)


@register.filter
def document_language_codes(source):
    explicit = _normalize_language_codes(source.get("language"))
    inferred = _language_codes_from_translations(source)
    return unique([*explicit, *inferred])


@register.simple_tag(takes_context=True)
def preferred_language(context, source):
    available = document_language_codes(source)
    if not available:
        return ""

    req_full, req_base = split_lang_code(context.get("LANGUAGE_CODE", ""))
    for lang in available:
        full, base = split_lang_code(lang)
        if req_full and full == req_full:
            return lang
        if req_base and base == req_base:
            return lang

    return available[0]


@register.filter
def first(value):
    items = as_list(value)
    return items[0] if items else ""


@register.filter
def normalize_doi(value):
    doi = first(value)
    if not doi:
        return ""
    return (
        str(doi)
        .strip()
        .replace("https://doi.org/", "")
        .replace("http://doi.org/", "")
        .replace("doi.org/", "")
    )


@register.filter
def doi_url(value):
    doi = normalize_doi(value)
    return f"https://doi.org/{doi}" if doi else ""


@register.filter
def orcid_url(value):
    return build_orcid_url(value)
