from django import template
from django.utils.translation import gettext as _

from search_gateway.transforms import apply_display_transform

register = template.Library()


def _format_display_value(value):
    if not value:
        return value

    normalized = str(value).strip()
    if normalized.lower() == "true":
        return _("Yes")
    if normalized.lower() == "false":
        return _("No")

    uppercase_words = {
        "cwts", "sjr", "snip", "issn", "apc", "usd", "sdg", "doi", "api", "url", "id",
    }
    lowercase_words = {
        "a", "an", "and", "as", "at", "but", "by", "for", "from", "in",
        "into", "of", "on", "or", "the", "to", "with", "is", "are", "vs",
        "o", "os", "um", "uma", "uns", "umas",
        "do", "da", "dos", "das", "de", "em", "no", "na", "nos", "nas",
        "ao", "à", "aos", "às", "por", "para", "com", "sem", "sob", "sobre",
    }

    words = normalized.replace("_", " ").split()
    result = []
    for i, word in enumerate(words):
        word_lower = word.lower()

        if word_lower in uppercase_words:
            result.append(word.upper())
        elif i > 0 and word_lower in lowercase_words:
            result.append(word_lower)
        else:
            result.append(word.capitalize())

    return " ".join(result)


@register.filter
def get_attr(obj, attr_name):
    if obj is None or not attr_name:
        return None
    if isinstance(obj, dict):
        return obj.get(attr_name)
    return getattr(obj, attr_name, None)


@register.filter
def ui_value(value, field_key=None):
    if value is None:
        return value

    raw = str(value).strip()

    if raw.lower() == "true":
        return _("Yes")
    if raw.lower() == "false":
        return _("No")

    if not field_key:
        return _format_display_value(raw)

    key = str(field_key).strip()

    if key in ("category_level", "category_type", "boolean"):
        transform_type = "boolean" if key == "boolean" else "category_level"
        transformed_value = apply_display_transform(transform_type, raw)
        if transformed_value not in (None, "") and transformed_value != raw:
            return transformed_value

    return _format_display_value(raw)
