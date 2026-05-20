from functools import lru_cache

from django.utils.translation import gettext as _
from iso639 import Lang
from pycountry import countries

from .models import DataSource
from .option_normalization import clean_text


def _resolve_data_source(data_source):
    if hasattr(data_source, "field_settings_dict") and hasattr(data_source, "get_field"):
        return data_source
    return DataSource.resolve(data_source)


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


def _get_category_level_display(value):
    return {
        "domain": _("Domain"),
        "field": _("Area"),
        "subfield": _("Subarea"),
        "topic": _("Topic"),
    }.get(clean_text(value).lower(), value)


def _get_scielo_collection_display(value):
    return {
        "arg": _("Argentina"),
        "bol": _("Bolivia"),
        "chl": _("Chile"),
        "cic": _("Science and Culture"),
        "col": _("Colombia"),
        "cri": _("Costa Rica"),
        "cub": _("Cuba"),
        "dom": _("Dominican Republic"),
        "ecu": _("Ecuador"),
        "esp": _("Spain"),
        "mex": _("Mexico"),
        "per": _("Peru"),
        "prt": _("Portugal"),
        "pry": _("Paraguay"),
        "psi": _("PEPSIC"),
        "rve": _("REVENF"),
        "scl": _("Brazil"),
        "spa": _("Public Health"),
        "sza": _("South Africa"),
        "ury": _("Uruguay"),
        "ven": _("Venezuela"),
        "wid": _("West Indies"),
    }.get(clean_text(value).lower(), value)


def _get_scope_display(value):
    return {
        "openalex": "OpenAlex",
        "scielo": "SciELO",
    }.get(clean_text(value).lower(), value)


def _get_document_type_display(value):
    return {
        "article": _("Article"),
        "book": _("Book"),
        "book-chapter": _("Book chapter"),
        "dataset": _("Dataset"),
        "preprint": _("Preprint"),
    }.get(clean_text(value).lower(), value)


def _get_source_type_display(value):
    return {
        "book": _("Book"),
        "book series": _("Book series"),
        "conference": _("Conference"),
        "ebook platform": _("eBook platform"),
        "journal": _("Journal"),
        "repository": _("Repository"),
    }.get(clean_text(value).lower(), value)


TRANSFORMS = {
    "language": _get_language_name,
    "country": _get_country_name,
    "boolean": _get_boolean_display,
    "category_level": _get_category_level_display,
    "scielo_collection": _get_scielo_collection_display,
    "scope": _get_scope_display,
    "document_type": _get_document_type_display,
    "source_type": _get_source_type_display,
}


def _get_static_option_label_from_field_settings(field_settings, field_name, value):
    normalized_value = clean_text(value).lower()
    if not normalized_value:
        return None

    static_options = (
        ((field_settings or {}).get(field_name, {}) or {})
        .get("settings", {})
        .get("static_options")
    ) or []

    for option in static_options:
        option_value = clean_text((option or {}).get("value")).lower()
        if option_value != normalized_value:
            continue

        option_label = (option or {}).get("label")
        if isinstance(option_label, str) and option_label:
            return _(option_label)
        return option_label or value

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

    transform_type = (
        (field_settings.get(field_name, {}) or {})
        .get("settings", {})
        .get("display_transform")
    )
    return apply_display_transform(transform_type, value)
