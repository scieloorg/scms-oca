from django.conf import settings

from harvest.language_normalizer import normalize_language_value

_DOI_PREFIXES = (
    "https://doi.org/",
    "http://doi.org/",
    "https://dx.doi.org/",
    "http://dx.doi.org/",
)

_WORK_TYPE_MAP = {
    "article": "article-journal",
    "book": "book",
    "book-chapter": "chapter",
    "chapter": "chapter",
    "dataset": "dataset",
    "preprint": "article",
    "review": "article-journal",
    "editorial": "article-journal",
    "letter": "article-journal",
    "paratext": "article-journal",
    "other": "article-journal",
    "journal": "article-journal",
}

_CONTAINER_TITLE_TYPES = frozenset({"article-journal", "article", "chapter", "review"})
_PUBLISHER_TYPES = frozenset({"book", "chapter", "dataset"})

_NAME_PARTICLES = frozenset({
    "da", "das", "de", "del", "della", "delle", "degli", "den", "der",
    "des", "di", "do", "dos", "du", "e",
    "el", "het", "la", "las", "le", "les", "lo", "los",
    "te", "ten", "ter",
    "al", "ben", "bin", "ibn",
    "van", "von",
})

_NAME_SUFFIXES = {
    "jr": "Jr.", "jr.": "Jr.", "junior": "Junior",
    "sr": "Sr.", "sr.": "Sr.", "senior": "Senior",
    "filho": "Filho", "filha": "Filha",
    "neto": "Neto", "neta": "Neta", "netto": "Netto",
    "sobrinho": "Sobrinho", "sobrinha": "Sobrinha",
    "ii": "II", "iii": "III", "iv": "IV", "v": "V",
}

def _deep_get(data, *keys, default=None):
    """Safely traverse nested dicts: ``_deep_get(d, "a", "b")`` → ``d["a"]["b"]``."""
    for key in keys:
        if not isinstance(data, dict):
            return default
        data = data.get(key)
        if data is None:
            return default
    return data

def _str_or_none(value):
    if value in (None, ""):
        return None
    return str(value).strip() or None


def _normalized_lang_pair(raw):
    """Return ``(normalized_lower, base_code)`` for matching ``*_with_lang`` entries.

    ``harvest.language_normalizer.normalize_language_value`` returns a single
    string, not a ``(code, base)`` tuple.
    """
    if raw in (None, ""):
        return None, None
    s = str(raw).strip()
    norm = normalize_language_value(s)
    norm_lc = norm.strip().lower()
    base = norm_lc.split("-")[0].split("_")[0]
    return norm_lc, base


def _split_matches_by_lang(items, field_name, lang_code, *, value_key=None):
    """Split ``*_with_lang`` entries into exact-match vs base-language-match lists."""
    if not isinstance(items, list):
        return [], []
    requested, requested_base = _normalized_lang_pair(lang_code)

    if not requested:
        return [], []

    key = value_key or field_name
    exact, base = [], []

    for item in items:
        if not isinstance(item, dict):
            continue
        value = item.get(key)
        if value in (None, ""):
            continue

        item_norm, item_base = _normalized_lang_pair(str(item.get("language") or ""))
        if not item_norm:
            continue

        if item_norm == requested:
            exact.append(value)
        elif item_base == requested_base:
            base.append(value)

    return exact, base


def _pick_localized(source, field_name, lang_code, *, value_key=None):
    """Pick a localised scalar: try ``<field>_with_lang`` first, fall back to ``<field>``."""
    items = source.get(f"{field_name}_with_lang")
    exact, base = _split_matches_by_lang(items, field_name, lang_code, value_key=value_key)
    return _str_or_none(exact[0] if exact else base[0] if base else source.get(field_name))


def _resolve_title(source, lang):
    return _pick_localized(source, "title", lang) or "Untitled"


def normalize_doi(doi):
    s = _str_or_none(doi)
    if not s:
        return None
    for prefix in _DOI_PREFIXES:
        if s.lower().startswith(prefix.lower()):
            return s[len(prefix):]
    return s


def _resolve_csl_type(type):
    if not type:
        return "article-journal"
    #normalized type
    key = str(type).strip().lower().replace(" ", "-")
    return _WORK_TYPE_MAP.get(key, "article-journal")


def _resolve_issued(source):
    year = source.get("publication_year")
    if year in (None, ""):
        return None
    try:
        return {"date-parts": [[int(str(year)[:4])]]}
    except (TypeError, ValueError):
        return None


def _resolve_container_title(source):
    sources_list = source.get("sources")
    if isinstance(sources_list, list) and sources_list:
        title = _deep_get(sources_list[0], "title")
        if title:
            return str(title)
    return ""


def _resolve_url(source):
    url = source.get("content_url")
    if isinstance(url, list) and url:
        url = url[0]
    return _str_or_none(url) or _str_or_none(_deep_get(source, "sources", "url"))


def _resolve_pages(source):
    bib = source.get("biblio") or {}
    if not isinstance(bib, dict):
        return None

    if bib.get("pages"):
        return str(bib["pages"])

    first, last = _str_or_none(bib.get("first_page")), _str_or_none(bib.get("last_page"))
    if first and last:
        return f"{first}-{last}"
    return first or last


def _resolve_biblio(source):
    bib = source.get("biblio") or {}
    if not isinstance(bib, dict):
        return None, None
    return _str_or_none(bib.get("volume")), _str_or_none(bib.get("issue"))


def _tokenize_name(name):
    """Split a name string into tokens, isolating commas as separate tokens."""
    return name.replace(",", " , ").split()


def _extract_suffix(tokens):
    """Pop the last token if it is a known name suffix; return canonical form."""
    if tokens and tokens[-1].lower() in _NAME_SUFFIXES:
        return _NAME_SUFFIXES[tokens.pop().lower()]
    return None


def _strip_trailing_commas(tokens):
    """Remove trailing comma tokens left after suffix extraction."""
    while tokens and tokens[-1] == ",":
        tokens.pop()


def _split_leading_particles(tokens):
    """Pop leading particle words from *tokens*, keeping at least one word."""
    particles = []
    while len(tokens) > 1 and tokens[0].lower() in _NAME_PARTICLES:
        particles.append(tokens.pop(0))
    return " ".join(particles) if particles else None


def _split_trailing_particles(tokens):
    """Extract particle words between given names and the last token (family).

    Scans backwards, keeping at least one word for the given name.
    Returns the joined particle string or *None*.
    """
    particles = []
    i = len(tokens) - 2
    while i > 0 and tokens[i].lower() in _NAME_PARTICLES:
        particles.insert(0, tokens[i])
        i -= 1
    return " ".join(particles) if particles else None, i


def _classify_particle(particle):
    """Lowercase-initial → dropping-particle; uppercase → non-dropping-particle."""
    return "dropping-particle" if particle[0].islower() else "non-dropping-particle"


def _build_csl_name(*, family=None, given=None, particle=None, suffix=None):
    """Assemble a CSL-JSON name dict from already-parsed parts."""
    if not family and not given:
        return None
    result = {}
    if family:
        result["family"] = family
    if given:
        result["given"] = given
    if particle:
        result[_classify_particle(particle)] = particle
    if suffix:
        result["suffix"] = suffix
    return result


def _parse_comma_name(tokens):
    """Parse ``Family, Given`` format → *(family, given, particle)*.

    Leading particles in the family segment (e.g. "da Silva, João")
    are extracted automatically.
    """
    comma_idx = tokens.index(",")
    family_tokens = tokens[:comma_idx]
    given_tokens = [t for t in tokens[comma_idx + 1:] if t != ","]

    particle = _split_leading_particles(family_tokens)
    family = " ".join(family_tokens) if family_tokens else None
    given = " ".join(given_tokens) if given_tokens else None
    return family, given, particle


def _parse_natural_name(tokens):
    """Parse ``Given [particles] Family`` format → *(family, given, particle)*.

    Particles between the given name and the last word are extracted
    by scanning backwards.
    """
    if len(tokens) == 1:
        return tokens[0], None, None

    family = tokens[-1]
    particle, boundary = _split_trailing_particles(tokens)
    given = " ".join(tokens[: boundary + 1])
    return family, given, particle


def _parse_name_parts(raw_name):
    """Best-effort split of a display name into CSL-JSON name-variable parts.

    Handles formats like::

      "João da Silva Jr."          → given / dropping-particle / family / suffix
      "da Silva, João"             → dropping-particle / family / given
      "Van Dyck, Peter"            → non-dropping-particle / family / given
      "Maria de los Santos Neto"   → given / dropping-particle / family / suffix
    """
    name = str(raw_name).strip()
    if not name:
        return None

    tokens = _tokenize_name(name)
    suffix = _extract_suffix(tokens)
    _strip_trailing_commas(tokens)

    if not tokens:
        return {"literal": name}

    if "," in tokens:
        family, given, particle = _parse_comma_name(tokens)
    else:
        family, given, particle = _parse_natural_name(tokens)

    return _build_csl_name(
        family=family or name,
        given=given,
        particle=particle,
        suffix=suffix,
    )


def _parse_author(authorship):
    if not isinstance(authorship, dict):
        return None
    name = _str_or_none(authorship.get("name"))
    if not name:
        return None
    return _parse_name_parts(name)


def _collect_authors(source):
    return [
        author
        for auth in (source.get("authorships") or [])
        if (author := _parse_author(auth)) is not None
    ]


def _add_if(item, key, value):
    """Set ``item[key] = value`` only when value is truthy."""
    if value:
        item[key] = value


def document_source_to_csl_item(source, *, doc_id, language_code=None):
    """Build one CSL-JSON object from an indexed document ``_source`` dict."""
    if not isinstance(source, dict):
        source = {}

    lang = language_code or getattr(settings, "LANGUAGE_CODE", None) or "en"
    csl_type = _resolve_csl_type(source.get("type"))
    volume, issue = _resolve_biblio(source)

    item = {
        "id": str(doc_id),
        "type": csl_type,
        "title": _resolve_title(source, lang),
    }
    _add_if(item, "issued", _resolve_issued(source))
    _add_if(item, "author", _collect_authors(source))
    _add_if(item, "DOI", normalize_doi(_deep_get(source, "ids", "doi")))
    url = (f"https://doi.org/{item['DOI']}" if item.get("DOI") else None) or _resolve_url(source)

    _add_if(item, "URL", url)

    if csl_type in _CONTAINER_TITLE_TYPES:
        _add_if(item, "container-title", _resolve_container_title(source))

    _add_if(item, "volume", volume)
    _add_if(item, "issue", issue)
    _add_if(item, "page", _resolve_pages(source))

    if csl_type in _PUBLISHER_TYPES:
        _add_if(item, "publisher", _str_or_none(
            _deep_get(source, "primary_location", "source", "host_organization_name"),
        ))

    _add_if(item, "language", _str_or_none(source.get("language")))

    return item


def documents_payload_to_csl_json(documents, *, language_code=None):
    items = []
    for entry in documents:
        if not isinstance(entry, dict):
            continue
        doc_id = entry.get("id")
        source = entry.get("source")
        if doc_id is None or not isinstance(source, dict):
            continue
        entry_lang = _str_or_none(entry.get("language_code"))
        items.append(document_source_to_csl_item(
            source,
            doc_id=str(doc_id),
            language_code=entry_lang or language_code,
        ))
    return items
