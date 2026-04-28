import functools
import re
from pathlib import Path

import citeproc_styles
from citeproc import (
    Citation,
    CitationItem,
    CitationStylesBibliography,
    CitationStylesStyle,
    formatter,
)
from citeproc.source.json import CiteProcJSON

from ..csl_json import CSLSourceExtractor

_CONTAINER_TITLE_TYPES = frozenset({"article-journal", "article", "chapter", "review"})
_PUBLISHER_TYPES = frozenset({"book", "chapter", "dataset"})


def _add_if(item, key, value):
    """Set ``item[key] = value`` only when value is truthy."""
    if value:
        item[key] = value


def build_csl_item(source, doc_id, *, language=None):
    """Build a CSL-JSON item (citation payload) from an indexed document source."""
    extractor = CSLSourceExtractor(source, language=language)
    csl_type = extractor.csl_type()

    item = {
        "id": str(doc_id),
        "type": csl_type,
        "title": extractor.title(),
    }
    _add_if(item, "issued", extractor.issued())
    _add_if(item, "author", extractor.authors_with_given_family())

    doi = extractor.doi()
    _add_if(item, "DOI", doi)
    _add_if(item, "URL", extractor.url(doi=doi))

    if csl_type in _CONTAINER_TITLE_TYPES:
        _add_if(item, "container-title", extractor.source_title())

    _add_if(item, "volume", extractor.volume())
    _add_if(item, "issue", extractor.issue())
    _add_if(item, "page", extractor.pages())

    if csl_type in _PUBLISHER_TYPES:
        _add_if(item, "publisher", extractor.publisher())

    _add_if(item, "language", extractor.source_language())

    return item


def build_csl_payload(documents, *, language=None):
    """Build a list of CSL-JSON items from a payload of ``{id, source, language_code}`` entries."""
    items = []
    for entry in documents:
        if not isinstance(entry, dict):
            continue
        doc_id = entry.get("id")
        source = entry.get("source")
        if doc_id is None or not isinstance(source, dict):
            continue
        entry_lang = entry.get("language_code")
        entry_lang = str(entry_lang).strip() if entry_lang not in (None, "") else None
        items.append(
            build_csl_item(
                source,
                doc_id=str(doc_id),
                language=entry_lang or language,
            )
        )
    return items


def _styles_dir():
    return Path(citeproc_styles.__file__).resolve().parent / "styles"


def get_style_filepath(style):
    path = _styles_dir() / f"{style}.csl"
    if not path.is_file():
        raise FileNotFoundError(f"CSL style not found: {style} ({path})")
    return str(path)


def _csl_info_title(path):
    try:
        chunk = path.read_text(encoding="utf-8", errors="ignore")[:98304]
    except OSError:
        return None
    info = re.search(r"<info>\s*([\s\S]*?)</info>", chunk, re.IGNORECASE)
    block = info.group(1) if info else chunk
    title = re.search(r"<title>([^<]+)</title>", block)
    return title.group(1).strip() if title else None


@functools.lru_cache(maxsize=1)
def list_installed_csl_styles():
    base = _styles_dir()
    if not base.is_dir():
        return []
    rows = []
    for path in sorted(base.glob("*.csl"), key=lambda p: p.stem.lower()):
        stem = path.stem
        label = _csl_info_title(path) or stem.replace("-", " ").title()
        rows.append({"id": stem, "label": label})
    rows.sort(key=lambda r: (r["label"].lower(), r["id"]))
    return rows


def render_citation(
    csl_json,
    *,
    style="apa",
    fmt=formatter.plain,
    validate=False,
):
    """
    Render bibliography strings for each CSL-JSON item using citeproc-py.

    ``style`` is the filename stem under citeproc_styles (e.g. ``bibtex``, ``apa``).
    """
    if not csl_json:
        return []

    bib_source = CiteProcJSON(csl_json)
    style_path = get_style_filepath(style)
    bib_style = CitationStylesStyle(style_path, validate=validate)
    bibliography = CitationStylesBibliography(bib_style, bib_source, fmt)

    def warn(_citation_item):
        pass

    for entry in csl_json:
        cid = entry.get("id")
        if cid is None:
            continue
        citation = Citation([CitationItem(str(cid))])
        bibliography.register(citation)
        bibliography.cite(citation, warn)

    return [str(item) for item in bibliography.bibliography()]


def render_bibtex(csl_json):
    parts = render_citation(csl_json, style="bibtex", fmt=formatter.plain, validate=False)
    return "\n\n".join(p.strip() for p in parts if p and str(p).strip())

