import re

from datetime import date, datetime

from django import template
from search.normalize import (
    as_list,
    deduplicate_variants_by_value,
    match_language,
    split_lang_code,
    unique,
)


register = template.Library()


@register.filter
def format_date_br(value):
    """Formata data string para dd/mm/aaaa."""
    if not value:
        return ""

    if isinstance(value, (datetime, date)):
        return value.strftime("%d/%m/%Y")

    match = re.match(r"^(\d{4})-(\d{2})-(\d{2})", value)
    if match:
        return f"{match.group(3)}/{match.group(2)}/{match.group(1)}"

    return value


@register.simple_tag(takes_context=True)
def localized_field(context, source, field_name, value_key=None, output="scalar"):
    """Return localized value from `<field>_with_lang` using the request language."""
    key = (value_key.strip() if value_key and value_key.strip() else None) or field_name
    items = source.get(f"{field_name}_with_lang") or []
    localized = match_language(items, context.get("LANGUAGE_CODE", ""), key)

    if str(output).strip().lower() == "list":
        return as_list(unique(localized) if localized else source.get(field_name))

    value = localized[0] if localized else None
    return value if value not in (None, "") else source.get(field_name)


@register.simple_tag(takes_context=True)
def field_variants(context, source, field_name, value_key=None, output="scalar"):
    """Return all language variants from `<field>_with_lang`, grouped by base code."""
    key = (value_key.strip() if value_key and value_key.strip() else None) or field_name
    as_list_output = str(output).strip().lower() == "list"
    items = source.get(f"{field_name}_with_lang") or []
    if not items:
        return []

    preferred_full, preferred_base = split_lang_code(context.get("LANGUAGE_CODE", ""))
    explicit_languages = {
        split_lang_code(language)[1]
        for language in as_list(source.get("language"))
        if split_lang_code(language)[1]
    }
    grouped = {}

    for item in items:
        if not isinstance(item, dict):
            continue

        code, base = split_lang_code(item.get("language"))
        if not base:
            continue

        raw_value = item.get(key)
        value = as_list(raw_value) if as_list_output else raw_value
        if value in (None, "", []):
            continue

        candidate = {"language": base, "value": value}
        current = grouped.get(base)

        if current is None:
            grouped[base] = candidate
        elif preferred_full and code == preferred_full:
            grouped[base] = candidate
        elif preferred_base and base == preferred_base and code == base:
            grouped[base] = candidate

    return deduplicate_variants_by_value(
        grouped.values(),
        explicit_languages=explicit_languages,
        preferred_language=preferred_base,
    )
