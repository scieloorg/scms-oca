from functools import lru_cache
from django.utils.translation import gettext as _
from iso639 import Lang
from pycountry import countries

from .data_sources_with_settings import get_display_transform_by_field_name

@lru_cache(maxsize=512)
def _get_language_name(code):
    try:
        return _(Lang(code).name)
    except:
        return code


@lru_cache(maxsize=512)
def _get_country_name(code):
    try:
        if code:
            country = countries.get(alpha_2=code.upper())
            if country:
                return _(country.name)
    except:
        pass
    return code

@lru_cache(maxsize=128)
def _get_boolean_display(code):
    """Cache boolean displays"""
    if code in (True, 1, "true", "1"):
        return _("Yes")
    elif code in (False, 0, "false", "0"):
        return _("No")
    return code

TRANSFORMS = {
    "language": _get_language_name,
    "country": _get_country_name,
    "boolean": _get_boolean_display,
}

@lru_cache(maxsize=256)
def _get_transform_type(data_source, field_name):
    """Cache transform type lookups"""
    return get_display_transform_by_field_name(data_source, field_name)

def apply_transform(data_source, field_name, code):
    transform_type = _get_transform_type(data_source, field_name)
    transform = TRANSFORMS.get(transform_type)
    if transform:
        try:
            return transform(code)
        except:
            return code
    return code

