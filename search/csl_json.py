from django.conf import settings

from .templatetags.custom_filters import _normalize_lang_code

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


def _split_matches_by_lang(items, field_name, lang_code, *, value_key=None):
    """Split ``*_with_lang`` entries into exact-match vs base-language-match lists."""
    if not isinstance(items, list):
        return [], []

    requested, requested_base = _normalize_lang_code(lang_code)
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

        item_norm, item_base = _normalize_lang_code(str(item.get("language") or ""))
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
    return (
        _pick_localized(source, "title", lang, value_key="text")
        or _pick_localized(source, "title", lang)
        or "Untitled"
    )


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


def _parse_display_name(display_name):
    name = str(display_name).strip()
    if not name:
        return None

    if "," in name:
        family, _, given = name.partition(",")
        return {"family": family.strip(), "given": given.strip() or None}

    parts = name.split()
    if len(parts) >= 2:
        return {"family": parts[-1], "given": " ".join(parts[:-1])}

    return {"literal": name}


def _parse_author(authorship):
    if not isinstance(authorship, dict):
        return None

    author = authorship.get("author")
    if isinstance(author, dict):
        display = author.get("display_name")
        if display:
            return _parse_display_name(display)

        family, given = _str_or_none(author.get("family")), _str_or_none(author.get("given"))
        if family or given:
            result = {}
            if family:
                result["family"] = family
            if given:
                result["given"] = given
            return result

    literal = _str_or_none(authorship.get("name"))
    return {"literal": literal} if literal else None


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
        items.append(document_source_to_csl_item(source, doc_id=str(doc_id), language_code=language_code))
    return items
