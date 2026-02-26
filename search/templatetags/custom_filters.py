from django import template
from datetime import date, datetime
import re
register = template.Library()


def _get_attr_or_key(data, key, default=None):
    if data is None:
        return default
    if isinstance(data, dict):
        return data.get(key, default)
    return getattr(data, key, default)


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


def _split_matches_by_lang(items, field_name, lang_code):
    if not isinstance(items, list):
        return [], []

    requested, requested_base = _normalize_lang_code(lang_code)
    if not requested:
        return [], []

    exact_matches = []
    base_matches = []

    for item in items:
        value = _get_attr_or_key(item, field_name)
        if value in (None, ""):
            continue

        item_lang = _get_attr_or_key(item, "language")
        item_lang_norm, item_lang_base = _normalize_lang_code(item_lang)
        if not item_lang_norm:
            continue

        if item_lang_norm == requested:
            exact_matches.append(value)
            continue

        if item_lang_base == requested_base:
            base_matches.append(value)

    return exact_matches, base_matches


def _pick_value_from_with_lang(items, field_name, lang_code):
    exact_matches, base_matches = _split_matches_by_lang(items, field_name, lang_code)
    if exact_matches:
        return exact_matches[0]
    if base_matches:
        return base_matches[0]
    return None

def _dedupe_keep_order(values):
    result = []
    seen = set()
    for value in values:
        marker = repr(value)
        if marker in seen:
            continue
        seen.add(marker)
        result.append(value)
    return result


def _pick_values_from_with_lang(items, field_name, lang_code):
    exact_matches, base_matches = _split_matches_by_lang(items, field_name, lang_code)
    if exact_matches:
        return _dedupe_keep_order(exact_matches)
    if base_matches:
        return _dedupe_keep_order(base_matches)
    return []


def _as_bool(value):
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y", "list", "many"}

@register.filter
def get_item(dictionary, key):
    """Retorna o valor de um dicionário usando uma chave dinâmica"""
    if dictionary is None:
        return []
    return dictionary.get(key, [])


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
        return f"{match.group(3)}-{match.group(2)}-{match.group(1)}"

    return value


@register.simple_tag(takes_context=True)
def get_localized_field(context, source, field_name, as_list=False):
    """
    Return localized field from `<field>_with_lang` using request language.

    If `as_list` is truthy, always return a list of values.
    Otherwise, return a scalar value.
    """
    language_code = _get_request_lang_code(context)
    base_value = _get_attr_or_key(source, field_name)
    with_lang_items = _get_attr_or_key(source, f"{field_name}_with_lang")

    if _as_bool(as_list):
        localized_values = _pick_values_from_with_lang(with_lang_items, field_name, language_code)
        if localized_values:
            return localized_values
        if isinstance(base_value, list):
            return base_value
        if base_value in (None, ""):
            return []
        return [base_value]

    localized_value = _pick_value_from_with_lang(with_lang_items, field_name, language_code)
    return localized_value if localized_value not in (None, "") else base_value
