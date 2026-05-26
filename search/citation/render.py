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

from .scientific_production import (
    SCIENTIFIC_PRODUCTION_CSV_COLUMNS,
    build_scientific_production_citation_item,
)
from .social_production import (
    build_social_production_citation_item,
    is_social_production_document,
)

_CSL_ITEM_KEYS = frozenset(
    {
        "id",
        "type",
        "title",
        "issued",
        "author",
        "DOI",
        "URL",
        "container-title",
        "volume",
        "issue",
        "page",
        "publisher",
        "language",
    }
)
_BIBTEX_TYPE_MAP = {
    "article": "article",
    "article-journal": "article",
    "book": "book",
    "chapter": "incollection",
    "dataset": "misc",
    "entry": "misc",
}


def _year_from_issued(issued):
    date_parts = (issued or {}).get("date-parts")
    if isinstance(date_parts, list) and date_parts and isinstance(date_parts[0], list) and date_parts[0]:
        return date_parts[0][0]
    return None


def build_citation_items(documents, *, language=None):
    """Build normalized citation dicts from indexed document payload entries."""
    items = []
    position = 0
    for entry in documents or []:
        if not isinstance(entry, dict):
            continue
        doc_id = entry.get("id")
        source = entry.get("source")
        if doc_id is None or not isinstance(source, dict):
            continue
        position += 1
        if is_social_production_document(entry):
            items.append(
                build_social_production_citation_item(
                    entry,
                    language=language,
                    position=position,
                )
            )
        else:
            items.append(
                build_scientific_production_citation_item(
                    entry,
                    language=language,
                    position=position,
                )
            )
    return items


def build_csl_payload(documents, *, language=None):
    """Build a list of CSL-JSON items from a payload of ``{id, source, language_code}`` entries."""
    return [
        {key: value for key, value in item.items() if key in _CSL_ITEM_KEYS}
        for item in build_citation_items(documents, language=language)
    ]


def citation_csv_columns(rows):
    columns = []
    for row in rows:
        for key in row:
            if key not in columns:
                columns.append(key)
    return tuple(columns) or SCIENTIFIC_PRODUCTION_CSV_COLUMNS


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

    citeproc_items = [
        {key: value for key, value in item.items() if key in _CSL_ITEM_KEYS}
        for item in csl_json
    ]
    bib_source = CiteProcJSON(citeproc_items)
    style_path = get_style_filepath(style)
    bib_style = CitationStylesStyle(style_path, validate=validate)
    bibliography = CitationStylesBibliography(bib_style, bib_source, fmt)

    def warn(_citation_item):
        pass

    for entry in citeproc_items:
        cid = entry.get("id")
        if cid is None:
            continue
        citation = Citation([CitationItem(str(cid))])
        bibliography.register(citation)
        bibliography.cite(citation, warn)

    return [str(item) for item in bibliography.bibliography()]


def _bibtex_escape(value):
    return str(value).replace("\\", "\\textbackslash{}").replace("{", "\\{").replace("}", "\\}")


def _bibtex_key(item):
    return re.sub(r"[^\w]", "", str(item.get("bibtex_key") or "")) or "item"


def _bibtex_authors(authors):
    if not isinstance(authors, list):
        return ""
    names = []
    for author in authors:
        if not isinstance(author, dict):
            continue
        if author.get("literal"):
            names.append(str(author["literal"]))
            continue
        family = author.get("family") or ""
        given = author.get("given") or ""
        name = f"{given} {family}".strip()
        if name:
            names.append(name)
    return " and ".join(names)


def _bibtex_fields(item):
    year = _year_from_issued(item.get("issued"))
    fields = [
        ("title", item.get("title")),
        ("author", _bibtex_authors(item.get("author"))),
        ("year", year),
        ("journal", item.get("container-title")),
        ("volume", item.get("volume")),
        ("number", item.get("issue")),
        ("pages", item.get("page")),
        ("publisher", item.get("publisher")),
        ("doi", item.get("DOI")),
        ("url", item.get("URL")),
        ("note", item.get("citation_text")),
    ]
    return [(key, value) for key, value in fields if value not in (None, "", [])]


def render_bibtex(csl_json):
    blocks = []
    for item in csl_json:
        entry_type = item.get("bibtex_type") or _BIBTEX_TYPE_MAP.get(item.get("type"), "misc")
        lines = [f"@{entry_type}{{{_bibtex_key(item)},"]
        lines.extend(
            f"  {key} = {{{_bibtex_escape(value)}}},"
            for key, value in _bibtex_fields(item)
        )
        lines.append("}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)

