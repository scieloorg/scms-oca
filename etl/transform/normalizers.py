import re
import unicodedata

import pycountry


def normalize_doi(doi: str | None) -> str | None:
    if not doi:
        return None

    normalized = str(doi).strip().lower()
    normalized = re.sub(r"^https?://(dx\.)?doi\.org/", "", normalized)
    normalized = re.sub(r"^doi:", "", normalized)
    normalized = re.sub(r"([0-9\-])([a-z]{2})$", r"\1", normalized)

    return normalized if re.match(r"^10\.\d{4,9}/\S+$", normalized) else None


def normalize_isbn(isbn: str | None) -> str | None:
    if not isbn:
        return None

    normalized = str(isbn).strip().replace("-", "").replace(" ", "")
    if len(normalized) == 10 and re.match(r"^\d{9}[\dX]$", normalized, re.IGNORECASE):
        return normalized.upper()
    if len(normalized) == 13 and normalized.isdigit():
        return normalized

    return None


def normalize_issn(issn: str | None) -> str | None:
    if not issn:
        return None

    normalized = re.sub(r"[^\dX]", "", str(issn).upper())
    if len(normalized) == 8:
        return f"{normalized[:4]}-{normalized[4:]}"
    return None


def normalize_text(text: str | None, strip_accents=True) -> str | None:
    if not text:
        return None

    stripped_text = str(text).strip()
    unicode_form = "NFKD" if strip_accents else "NFC"
    unicode_normalized_text = unicodedata.normalize(unicode_form, stripped_text)

    if strip_accents:
        unicode_normalized_text = "".join(
            char for char in unicode_normalized_text if not unicodedata.combining(char)
        )

    whitespace_normalized_text = re.sub(r"\s+", " ", unicode_normalized_text)
    return whitespace_normalized_text if whitespace_normalized_text else None


def normalize_author_name(name: str | None, strip_accents=True) -> str:
    if not name:
        return ""

    lowercased_name = str(name).lower().strip()
    dash_normalized_name = (
        lowercased_name.replace("\u2010", "-")
        .replace("\u2013", "-")
        .replace("\u2014", "-")
    )
    whitespace_normalized_name = " ".join(dash_normalized_name.split())
    unicode_form = "NFKD" if strip_accents else "NFC"
    unicode_normalized_name = unicodedata.normalize(
        unicode_form, whitespace_normalized_name
    )

    if strip_accents:
        unicode_normalized_name = "".join(
            char for char in unicode_normalized_name if not unicodedata.combining(char)
        )

    return unicode_normalized_name


def normalize_keywords(keywords: list[str] | None) -> list[str]:
    if not keywords:
        return []

    normalized = {
        normalized_keyword.lower()
        for keyword in keywords
        if (normalized_keyword := normalize_text(keyword))
    }
    return sorted(normalized)


def int_or_none(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def as_list(value: Any) -> list:
    if value in (None, [], {}):
        return []
    return value if isinstance(value, list) else [value]


def unique(values: list) -> list:
    return list(dict.fromkeys(value for value in values if value))


def scalar_or_list(values: list):
    values = unique(values)
    return values[0] if len(values) == 1 else values


def normalize_language(language: str | None) -> str | None:
    if not language:
        return None

    language_value = str(language).strip()

    if len(language_value) == 2 and language_value.isalpha():
        result = pycountry.languages.get(alpha_2=language_value.lower())
        if result:
            return result.alpha_2

    if len(language_value) == 3 and language_value.isalpha():
        result = pycountry.languages.get(alpha_3=language_value.lower())
        if result and hasattr(result, "alpha_2"):
            return result.alpha_2

        result = pycountry.languages.get(bibliographic=language_value.lower())
        if result and hasattr(result, "alpha_2"):
            return result.alpha_2

    language_lower = language_value.lower()
    for language_item in pycountry.languages:
        if hasattr(language_item, "name") and language_item.name.lower() == language_lower:
            if hasattr(language_item, "alpha_2"):
                return language_item.alpha_2
        if (
            hasattr(language_item, "common_name")
            and language_item.common_name.lower() == language_lower
        ):
            if hasattr(language_item, "alpha_2"):
                return language_item.alpha_2

    return None


def normalize_country_code(country: str | None) -> str | None:
    if not country:
        return None

    country_value = str(country).strip()

    if len(country_value) == 2 and country_value.isalpha():
        result = pycountry.countries.get(alpha_2=country_value.upper())
        if result:
            return result.alpha_2

    if len(country_value) == 3 and country_value.isalpha():
        result = pycountry.countries.get(alpha_3=country_value.upper())
        if result:
            return result.alpha_2

    try:
        result = pycountry.countries.search_fuzzy(country_value)
        if result:
            return result[0].alpha_2
    except (LookupError, ValueError):
        pass

    try:
        result = pycountry.countries.lookup(country_value)
        if result:
            return result.alpha_2
    except (LookupError, KeyError):
        pass

    return None
