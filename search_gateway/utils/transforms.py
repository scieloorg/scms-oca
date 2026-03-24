from functools import lru_cache

from django.utils.translation import gettext as _
from iso639 import Lang
from pycountry import countries

from ..models import DataSource


TRUE_VALUES = {"true", "1", "yes", "y", "sim"}
FALSE_VALUES = {"false", "0", "no", "n", "nao"}


def _get_language_name(code):
    try:
        return _(Lang(code).name)
    except Exception:
        return code


@lru_cache(maxsize=512)
def _get_country_name(code):
    try:
        if code:
            country = countries.get(alpha_2=code.upper())
            if country:
                return _(country.name)
    except Exception:
        pass
    return code


@lru_cache(maxsize=128)
def _get_boolean_display(code):
    if code in (True, 1, "true", "1"):
        return _("Yes")
    if code in (False, 0, "false", "0"):
        return _("No")
    return code


TRANSFORMS = {
    "language": _get_language_name,
    "country": _get_country_name,
    "boolean": _get_boolean_display,
    "category_level": lambda value: {
        "domain": _("Domain"),
        "field": _("Area"),
        "subfield": _("Subarea"),
        "topic": _("Topic"),
    }.get(str(value or "").strip().lower(), value),
}


def _resolve_data_source(data_source):
    if isinstance(data_source, DataSource):
        return data_source
    return DataSource.resolve(data_source)


def _get_static_option_label_from_field_settings(field_settings, field_name, value):
    normalized_value = str(value or "")
    if not normalized_value:
        return None

    field_config = field_settings.get(field_name)
    if not field_config:
        return None

    static_options = (field_config.get("settings") or {}).get("static_options") or []
    for option in static_options:
        if str(option["value"]) == normalized_value:
            label = option.get("label")
            return _(label) if isinstance(label, str) and label else value

    return None


def coerce_boolean(value):
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in TRUE_VALUES:
            return True
        if normalized in FALSE_VALUES:
            return False
        return None

    if value in (True, 1):
        return True
    if value in (False, 0):
        return False
    return None


@lru_cache(maxsize=256)
def _get_transform_type(data_source, field_name):
    resolved_data_source = _resolve_data_source(data_source)
    if not resolved_data_source:
        return None
    field = resolved_data_source.get_field(field_name)
    return field.display_transform if field else None


def apply_display_transform(transform_type, value):
    transform = TRANSFORMS.get(transform_type)
    if not transform:
        return value
    try:
        return transform(value)
    except Exception:
        return value


def apply_transform(data_source, field_name, code):
    resolved_data_source = _resolve_data_source(data_source)
    field_settings = resolved_data_source.field_settings_dict if resolved_data_source else {}
    static_option_label = _get_static_option_label_from_field_settings(field_settings, field_name, code)
    if static_option_label is not None:
        return static_option_label

    transform_type = _get_transform_type(data_source, field_name)
    return apply_display_transform(transform_type, code)


def apply_display_transform_from_field_settings(field_settings, field_name, value):
    static_option_label = _get_static_option_label_from_field_settings(field_settings, field_name, value)
    if static_option_label is not None:
        return static_option_label

    field_config = field_settings.get(field_name) or {}
    transform_type = (field_config.get("settings") or {}).get("display_transform")
    return apply_display_transform(transform_type, value)
