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


def deduplicate_variants_by_value(
    variants,
    explicit_languages=None,
    preferred_language=None,
):
    def normalized_value_key(value):
        if isinstance(value, (list, tuple)):
            return tuple(normalized_value_key(item) for item in value)

        return " ".join(str(value or "").strip().split()).lower()

    explicit_languages = set(explicit_languages or [])
    preferred_language = preferred_language or ""
    unique_variants = {}

    for position, variant in enumerate(variants):
        marker = normalized_value_key(variant["value"])
        priority = (
            0 if variant["language"] in explicit_languages else 1,
            0 if preferred_language and variant["language"] == preferred_language else 1,
            position,
        )
        current = unique_variants.get(marker)
        if current is None or priority < current[0]:
            unique_variants[marker] = (priority, variant)

    return [item[1] for item in sorted(unique_variants.values(), key=lambda item: item[0])]


def normalize_orcid(value):
    orcid_prefixes = (
        "https://orcid.org/",
        "http://orcid.org/",
        "orcid.org/",
    )
    items = as_list(value)
    if not items:
        return ""

    orcid = str(items[0]).strip()
    lower_orcid = orcid.lower()
    for prefix in orcid_prefixes:
        if lower_orcid.startswith(prefix):
            return orcid[len(prefix):]

    return orcid


def orcid_url(value):
    orcid = normalize_orcid(value)
    return f"https://orcid.org/{orcid}" if orcid else ""
