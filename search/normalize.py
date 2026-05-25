from harvest.language_normalizer import normalize_language_field


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


def normalize_language_codes(value):
    codes = []
    for code in as_list(normalize_language_field(value)):
        _, base = split_lang_code(code)
        if base:
            codes.append(base)
    return unique(codes)


def language_codes_from_translations(source):
    codes = []
    explicit = set(normalize_language_codes(source.get("language")))

    for key, value in source.items():
        if not str(key).endswith("_with_lang") or not isinstance(value, list):
            continue

        value_key = str(key)[: -len("_with_lang")]
        variants = []

        for item in value:
            if not isinstance(item, dict):
                continue

            raw_value = item.get(value_key)
            if raw_value in (None, "", []):
                continue

            for code in normalize_language_codes(item.get("language")):
                _, base = split_lang_code(code)
                if not base:
                    continue

                variants.append({"language": base, "value": raw_value})

        for variant in deduplicate_variants_by_value(
            variants,
            explicit_languages=explicit,
        ):
            base = variant["language"]
            if base not in codes:
                codes.append(base)

    return codes


def document_language_codes(source):
    explicit = normalize_language_codes(source.get("language"))
    inferred = language_codes_from_translations(source)
    return unique([*explicit, *inferred])


def match_language(items, lang_code, key):
    requested, requested_base = split_lang_code(lang_code)
    if not requested:
        return []

    exact = []
    base = []

    for item in items:
        if not isinstance(item, dict):
            continue

        value = item.get(key)
        if value in (None, ""):
            continue

        item_code, item_base = split_lang_code(item.get("language"))
        if not item_code:
            continue

        if item_code == requested:
            exact.append(value)
        elif item_base == requested_base:
            base.append(value)

    return exact or base


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


def normalize_author_text(value):
    text = str(value or "").strip()
    if "," in text:
        family, given = text.split(",", 1)
        text = f"{given} {family}"
    return " ".join(text.casefold().replace(",", " ").split())


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


def authorship_identity(authorship):
    if not isinstance(authorship, dict):
        return ("raw", repr(authorship))

    author = authorship.get("author") or {}
    name = (
        author.get("display_name")
        or authorship.get("raw_author_name")
        or authorship.get("name")
    )
    author_id = author.get("id") or authorship.get("id") or ""
    orcid = normalize_orcid(author.get("orcid") or authorship.get("orcid"))
    name_key = normalize_author_text(name)
    if name_key:
        return ("name", name_key)
    if orcid:
        return ("orcid", normalize_author_text(orcid))
    if author_id:
        return ("id", normalize_author_text(author_id))

    return ("raw", repr(authorship))


def unique_authorships(authorships):
    unique_items = []
    seen = set()

    for authorship in authorships or []:
        key = authorship_identity(authorship)
        if key in seen:
            continue
        seen.add(key)
        unique_items.append(authorship)

    return unique_items
