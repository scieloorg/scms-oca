import re
import unicodedata

try:
    from iso639 import Lang
except Exception:  # pragma: no cover - optional dependency at runtime
    Lang = None


# Common ISO 639-2 -> ISO 639-1 mappings used by our sources.
ISO639_2_TO_1 = {
    "eng": "en",
    "por": "pt",
    "fre": "fr",
    "fra": "fr",
    "spa": "es",
    "ger": "de",
    "deu": "de",
    "ita": "it",
    "rus": "ru",
    "jpn": "ja",
    "zho": "zh",
    "chi": "zh",
    "kor": "ko",
}


SYNONYM_TO_ISO639_1 = {
    # English
    "english": "en",
    "ingles": "en",
    "en us": "en",
    # Portuguese
    "portuguese": "pt",
    "portugues": "pt",
    # French
    "french": "fr",
    "francais": "fr",
    "frances": "fr",
    # Spanish
    "spanish": "es",
    "castilian": "es",
    "espanol": "es",
    "espanhol": "es",
    "castellano": "es",
    "spanish sign language": "es",
    "spanish castilian": "es",
}


_ALPHA_CODE_RE = re.compile(r"^[a-zA-Z]+$")
_SPACE_RE = re.compile(r"\s+")


def _normalize_key(value):
    text = unicodedata.normalize("NFKD", value)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = _SPACE_RE.sub(" ", text).strip()
    return text


def _resolve_with_iso639(value):
    if not Lang:
        return None
    try:
        if len(value) > 3:
            value = value.capitalize()
        elif len(value) > 4:
            value = value.lower()
        lang = Lang(value)
        code = getattr(lang, "pt1", None)
        if not code:
            code = getattr(lang, "pt2", None)
            return code
        if code and len(code) == 2:
            return code.lower()
    except Exception:
        return None
    return None


def normalize_language_value(value):
    """
    Normalize language values to ISO 639-1.

    If value cannot be normalized, return it unchanged.
    """
    if not isinstance(value, str):
        return value

    if not value.strip():
        return value
 
    key = _normalize_key(value)

    if len(key) == 2 and _ALPHA_CODE_RE.match(key):
        return key

    synonym = SYNONYM_TO_ISO639_1.get(key)
    if synonym:
        return synonym

    code = _resolve_with_iso639(key)
    if code:
        return code

    return value


def normalize_language_field(value):
    """
    Normalize a language field that can be a scalar or a list.

    For list values, deduplicate while preserving order.
    """
    if isinstance(value, list):
        normalized = []
        seen = set()
        for item in value:
            norm = normalize_language_value(item)
            if norm in (None, ""):
                continue
            marker = repr(norm)
            if marker in seen:
                continue
            seen.add(marker)
            normalized.append(norm)
        return normalized

    return normalize_language_value(value)
