from django import template

from search.normalize import (
    as_list,
    document_language_codes as normalize_document_language_codes,
    unique_authorships as normalize_unique_authorships,
    orcid_url as build_orcid_url,
    split_lang_code,
)


register = template.Library()


@register.filter
def unique_authorships(authorships):
    return normalize_unique_authorships(authorships)


@register.filter
def document_language_codes(source):
    return normalize_document_language_codes(source)


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
