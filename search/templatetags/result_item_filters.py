from django import template

from harvest.language_normalizer import normalize_language_field
from search.value_utils import dedupe_keep_order, get_attr_or_key


register = template.Library()


def normalize_sequence(value):
    if value in (None, ""):
        return []

    if isinstance(value, (list, tuple, set)):
        values = value
    else:
        values = [value]

    normalized_values = []
    for item in values:
        if item in (None, ""):
            continue

        if isinstance(item, str):
            item = item.strip()
            if not item:
                continue

        normalized_values.append(item)

    return dedupe_keep_order(normalized_values)


def iter_items(data):
    if isinstance(data, dict):
        return data.items()

    if hasattr(data, "__dict__"):
        return vars(data).items()

    return []


def collect_with_lang_codes(source):
    collected_codes = []
    for field_name, field_value in iter_items(source):
        if not str(field_name).endswith("_with_lang") or not isinstance(field_value, list):
            continue

        for item in field_value:
            language = get_attr_or_key(item, "language")
            normalized = normalize_language_field(language)

            for code in normalize_sequence(normalized):
                _, base_code = normalize_lang_code(code)
                if base_code and base_code not in collected_codes:
                    collected_codes.append(base_code)

    return collected_codes


def normalize_lang_code(lang_code):
    if not lang_code:
        return "", ""

    code = str(lang_code).strip().lower().replace("_", "-")
    return code, code.split("-")[0]


@register.filter
def language_codes(value):
    normalized_codes = []
    for code in normalize_sequence(normalize_language_field(value)):
        _, base_code = normalize_lang_code(code)
        if base_code:
            normalized_codes.append(base_code)
    return dedupe_keep_order(normalized_codes)


@register.filter
def document_language_codes(source):
    explicit_codes = language_codes(get_attr_or_key(source, "language"))
    inferred_codes = collect_with_lang_codes(source)
    return dedupe_keep_order([*explicit_codes, *inferred_codes])


@register.simple_tag(takes_context=True)
def get_preferred_document_language(context, source):
    available_codes = document_language_codes(source)
    if not available_codes:
        return ""

    request = context.get("request")
    requested_language = None
    if request is not None:
        requested_language = getattr(request, "lang", None) or getattr(request, "LANGUAGE_CODE", None)
    if not requested_language:
        requested_language = context.get("LANGUAGE_CODE")

    requested_full, requested_base = normalize_lang_code(requested_language)
    for language_code in available_codes:
        full_code, base_code = normalize_lang_code(language_code)
        if requested_full and full_code == requested_full:
            return language_code
        if requested_base and base_code == requested_base:
            return language_code

    return available_codes[0]


@register.filter
def first_item(value):
    normalized_values = normalize_sequence(value)
    return normalized_values[0] if normalized_values else ""


@register.filter
def normalize_doi(value):
    doi = first_item(value)
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
