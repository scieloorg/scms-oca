def unique(values):
    result = []
    seen = set()

    for value in values:
        marker = repr(value)
        if marker not in seen:
            seen.add(marker)
            result.append(value)

    return result


def split_lang_code(lang_code):
    if not lang_code:
        return "", ""

    code = str(lang_code).strip().lower().replace("_", "-")
    return code, code.split("-")[0]


def as_list(value):
    if value in (None, ""):
        return []

    if isinstance(value, (list, tuple, set)):
        values = value
    else:
        values = [value]

    normalized = []
    for item in values:
        if item in (None, ""):
            continue

        if isinstance(item, str):
            item = item.strip()
            if not item:
                continue

        normalized.append(item)

    return unique(normalized)


_ORCID_PREFIXES = (
    "https://orcid.org/",
    "http://orcid.org/",
    "orcid.org/",
)


def normalize_orcid(value):
    items = as_list(value)
    if not items:
        return ""

    orcid = str(items[0]).strip()
    lower_orcid = orcid.lower()
    for prefix in _ORCID_PREFIXES:
        if lower_orcid.startswith(prefix):
            return orcid[len(prefix):]

    return orcid


def orcid_url(value):
    orcid = normalize_orcid(value)
    return f"https://orcid.org/{orcid}" if orcid else ""
