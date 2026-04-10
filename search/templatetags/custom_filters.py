import re

from datetime import date, datetime

from django import template
from search.value_utils import dedupe_keep_order, get_attr_or_key


register = template.Library()


def _normalize_lang_code(lang_code):
    if not lang_code:
        return "", ""
    code = str(lang_code).strip().lower().replace("_", "-")
    return code, code.split("-")[0]


def _get_request_lang_code(context):
    request = context.get("request")
    if request is not None:
        lang = getattr(request, "lang", None) or getattr(request, "LANGUAGE_CODE", None)
        if lang:
            return lang
    return context.get("LANGUAGE_CODE")


def _get_with_lang_items(source, field_name):
    items = get_attr_or_key(source, f"{field_name}_with_lang")
    return items if isinstance(items, list) else []


def _get_preferred_localized_values(items, lang_code, key):
    requested, requested_base = _normalize_lang_code(lang_code)
    if not requested:
        return []

    exact_matches = []
    base_matches = []

    for item in items:
        value = get_attr_or_key(item, key)
        if value in (None, ""):
            continue

        item_lang = get_attr_or_key(item, "language")
        item_lang_norm, item_lang_base = _normalize_lang_code(item_lang)
        if not item_lang_norm:
            continue

        if item_lang_norm == requested:
            exact_matches.append(value)
            continue

        if item_lang_base == requested_base:
            base_matches.append(value)

    return exact_matches or base_matches


def _as_bool(value):
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y", "list", "many"}


def _parse_localized_tag_args(args):
    value_key = None
    as_list = False

    for arg in args:
        if _as_bool(arg):
            as_list = True
        elif value_key is None and arg:
            value_key = str(arg).strip() or None

    return value_key, as_list


def _normalize_variant_value(value, as_list):
    if as_list:
        if isinstance(value, list):
            values = [entry for entry in value if entry not in (None, "")]
        elif value in (None, ""):
            values = []
        else:
            values = [value]
        return dedupe_keep_order(values)

    return None if value in (None, "") else value


@register.filter
def format_date_br(value):
    """Formata data string para dd/mm/aaaa."""
    if not value:
        return ""

    if isinstance(value, datetime):
        return value.strftime("%d/%m/%Y")

    if isinstance(value, date):
        return value.strftime("%d/%m/%Y")

    match = re.match(r"^(\d{4})-(\d{2})-(\d{2})", value)
    if match:
        return f"{match.group(3)}/{match.group(2)}/{match.group(1)}"

    return value


@register.simple_tag(takes_context=True)
def get_localized_field(context, source, field_name, *args):
    """
    Return localized field from `<field>_with_lang` using request language.

    Optional 4th arg: value_key (e.g. "text") — key used inside each item to get
    the value. Defaults to field_name. Use when items use {"language": "x", "text": "..."}.

    Optional 4th/5th arg: "list" (or truthy) — return list of values instead of scalar.
    """
    value_key, as_list = _parse_localized_tag_args(args)
    key = value_key if value_key else field_name

    language_code = _get_request_lang_code(context)
    base_value = get_attr_or_key(source, field_name)
    with_lang_items = _get_with_lang_items(source, field_name)
    localized_values = _get_preferred_localized_values(with_lang_items, language_code, key)

    if as_list:
        if localized_values:
            return localized_values
        if isinstance(base_value, list):
            return base_value
        if base_value in (None, ""):
            return []
        return [base_value]

    localized_value = localized_values[0] if localized_values else None
    return localized_value if localized_value not in (None, "") else base_value


@register.simple_tag(takes_context=True)
def get_field_language_variants(context, source, field_name, *args):
    """
    Return all language variants available in `<field>_with_lang`.

    Each variant is returned as `{"language": "<base-code>", "value": ...}` so
    templates can render every available translation and let the client switch
    between them. Regional codes such as `pt-br` are collapsed to their base
    code (`pt`), preferring the request language variant when more than one maps
    to the same base code.
    """
    value_key, as_list = _parse_localized_tag_args(args)
    key = value_key if value_key else field_name
    with_lang_items = _get_with_lang_items(source, field_name)
    if not with_lang_items:
        return []

    preferred_language = _get_request_lang_code(context)
    preferred_full, preferred_base = _normalize_lang_code(preferred_language)
    grouped_variants = {}

    for item in with_lang_items:
        language_code, base_language_code = _normalize_lang_code(get_attr_or_key(item, "language"))
        if not base_language_code:
            continue

        value = _normalize_variant_value(get_attr_or_key(item, key), as_list)
        if value in (None, []):
            continue

        candidate = {
            "language": base_language_code,
            "value": value,
        }
        current = grouped_variants.get(base_language_code)
        if current is None:
            grouped_variants[base_language_code] = candidate
            continue

        if preferred_full and language_code == preferred_full:
            grouped_variants[base_language_code] = candidate
            continue

        if preferred_base and base_language_code == preferred_base and language_code == base_language_code:
            grouped_variants[base_language_code] = candidate
            continue

    return list(grouped_variants.values())
