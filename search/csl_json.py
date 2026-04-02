"""
Map OpenSearch document ``source`` dicts (OpenAlex-shaped and similar) to CSL-JSON items.
"""

from django.conf import settings
from .templatetags.custom_filters import _normalize_lang_code


def _get(d, *keys, default=None):
    cur = d
    for k in keys:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(k)
        if cur is None:
            return default
    return cur if cur is not None else default


def _split_matches_by_lang(
    items,
    field_name,
    lang_code,
    *,
    value_key=None,
):
    """
        Separa valores de listas *_with_lang em “match exato” vs “mesmo idioma base” (ex. pt vs pt-BR).
    """
    if not isinstance(items, list):
        return [], []

    requested, requested_base = _normalize_lang_code(lang_code)
    if not requested:
        return [], []

    key = value_key if value_key else field_name
    exact_matches = []
    base_matches = []

    for item in items:
        if not isinstance(item, dict):
            continue
        value = item.get(key)
        if value in (None, ""):
            continue

        item_lang = item.get("language")
        item_lang_norm, item_lang_base = _normalize_lang_code(
            str(item_lang) if item_lang is not None else ""
        )
        if not item_lang_norm:
            continue

        if item_lang_norm == requested:
            exact_matches.append(value)
        elif item_lang_base == requested_base:
            base_matches.append(value)

    return exact_matches, base_matches


def _pick_localized_scalar(
    source,
    field_name,
    language_code,
    *,
    value_key=None,
):
    items = source.get(f"{field_name}_with_lang")
    exact, base = _split_matches_by_lang(
        items, field_name, language_code, value_key=value_key
    )
    if exact:
        return str(exact[0])
    if base:
        return str(base[0])
    base_value = source.get(field_name)
    if base_value in (None, ""):
        return None
    return str(base_value)


def normalize_doi(doi):
    if doi is None:
        return None
    s = str(doi).strip()
    if not s:
        return None
    for prefix in (
        "https://doi.org/",
        "http://doi.org/",
        "https://dx.doi.org/",
        "http://dx.doi.org/",
    ):
        if s.lower().startswith(prefix.lower()):
            return s[len(prefix) :]
    return s


def _container_title(source):
    for key in ("resolved_source_name", "primary_source_title"):
        v = source.get(key)
        if v:
            return str(v)
    pl = source.get("primary_location") or {}
    if isinstance(pl, dict):
        src = pl.get("source") or {}
        if isinstance(src, dict):
            for key in ("display_name", "title"):
                v = src.get(key)
                if v:
                    return str(v)
    v = source.get("source_name")
    return str(v) if v else ""


def _content_url(source):
    u = source.get("content_url")
    if isinstance(u, list) and u:
        u = u[0]
    if isinstance(u, str) and u.strip():
        return u.strip()
    su = _get(source, "sources", "url")
    if isinstance(su, str) and su.strip():
        return su.strip()
    return None


def _pages(source):
    bib = source.get("biblio") or {}
    if not isinstance(bib, dict):
        return ""
    if bib.get("pages"):
        return str(bib["pages"])
    fp, lp = bib.get("first_page"), bib.get("last_page")
    if fp is not None or lp is not None:
        a, b = fp or "", lp or ""
        if a and b:
            return f"{a}-{b}"
        return str(a or b)
    return ""


def _issued_date_parts(source):
    y = source.get("publication_year")
    if y is None or y == "":
        return None
    try:
        yi = int(str(y)[:4])
        return [[yi]]
    except (TypeError, ValueError):
        return None


def _map_work_type(raw):
    if not raw:
        return "article-journal"
    t = str(raw).strip().lower().replace(" ", "-")
    mapping = {
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
    return mapping.get(t, "article-journal")


def _author_from_authorship(auth):
    if not isinstance(auth, dict):
        return None
    author = auth.get("author")
    if isinstance(author, dict):
        display = author.get("display_name")
        if display:
            display = str(display).strip()
            if "," in display:
                fam, _, given = display.partition(",")
                return {
                    "family": fam.strip(),
                    "given": given.strip() or None,
                }
            parts = display.split()
            if len(parts) >= 2:
                return {
                    "family": parts[-1],
                    "given": " ".join(parts[:-1]),
                }
            return {"literal": display}
        family = author.get("family")
        given = author.get("given")
        if family or given:
            out = {}
            if family:
                out["family"] = str(family)
            if given:
                out["given"] = str(given)
            return out or None
    name = auth.get("name")
    if name and str(name).strip():
        return {"literal": str(name).strip()}
    return None


def _collect_authors(source):
    authors = []
    for auth in source.get("authorships") or []:
        if isinstance(auth, dict):
            item = _author_from_authorship(auth)
            if item:
                authors.append(item)
    return authors


def document_source_to_csl_item(
    source,
    *,
    doc_id,
    language_code=None,
):
    """Build one CSL-JSON object from an indexed document ``_source`` dict."""
    if not isinstance(source, dict):
        source = dict()

    lang = language_code or getattr(settings, "LANGUAGE_CODE", None) or "en"

    title = _pick_localized_scalar(source, "title", lang, value_key="text")
    if not title:
        title = _pick_localized_scalar(source, "title", lang)
    if not title:
        title = "Untitled"

    issued = _issued_date_parts(source)
    ctype = _map_work_type(source.get("type"))

    item = {
        "id": str(doc_id),
        "type": ctype,
        "title": title,
    }

    if issued:
        item["issued"] = {"date-parts": issued}

    authors = _collect_authors(source)
    if authors:
        item["author"] = authors

    doi = normalize_doi(_get(source, "ids", "doi"))
    if doi:
        item["DOI"] = doi

    url = _content_url(source)
    if not url and doi:
        url = f"https://doi.org/{doi}"
    if url:
        item["URL"] = url

    ct = _container_title(source)
    if ct and ctype in (
        "article-journal",
        "article",
        "chapter",
        "review",
    ):
        item["container-title"] = ct

    bib = source.get("biblio") or {}
    if isinstance(bib, dict):
        if bib.get("volume"):
            item["volume"] = str(bib["volume"])
        if bib.get("issue"):
            item["issue"] = str(bib["issue"])

    pages = _pages(source)
    if pages:
        item["page"] = pages

    publisher = _get(source, "primary_location", "source", "host_organization_name")
    if publisher and ctype in ("book", "chapter", "dataset"):
        item["publisher"] = str(publisher)

    lang_code = source.get("language")
    if isinstance(lang_code, str) and lang_code.strip():
        item["language"] = lang_code.strip()

    return item


def documents_payload_to_csl_json(
    documents,
    *,
    language_code=None,
):
    out = []
    for entry in documents:
        if not isinstance(entry, dict):
            continue
        doc_id = entry.get("id")
        source = entry.get("source")
        if doc_id is None or not isinstance(source, dict):
            continue
        out.append(
            document_source_to_csl_item(
                source,
                doc_id=str(doc_id),
                language_code=language_code,
            )
        )
    return out
