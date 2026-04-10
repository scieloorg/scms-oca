from django import template

from harvest.language_normalizer import normalize_language_field
from search.normalize import as_list, split_lang_code, unique


register = template.Library()


def _language_codes_from_translations(source):
    codes = []
    for key, value in source.items():
        if not str(key).endswith("_with_lang") or not isinstance(value, list):
            continue

        for item in value:
            for code in as_list(normalize_language_field(item.get("language"))):
                _, base = split_lang_code(code)
                if base and base not in codes:
                    codes.append(base)

    return codes


def _normalize_language_codes(value):
    codes = []
    for code in as_list(normalize_language_field(value)):
        _, base = split_lang_code(code)
        if base:
            codes.append(base)
    return unique(codes)
