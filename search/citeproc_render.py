from __future__ import annotations

from pathlib import Path

from citeproc import (
    Citation,
    CitationItem,
    CitationStylesBibliography,
    CitationStylesStyle,
    formatter,
)
from citeproc.source.json import CiteProcJSON

import citeproc_styles


def get_style_filepath(style: str) -> str:
    base = Path(citeproc_styles.__file__).resolve().parent / "styles"
    path = base / f"{style}.csl"
    if not path.is_file():
        raise FileNotFoundError(f"CSL style not found: {style} ({path})")
    return str(path)


def render_citation(
    csl_json: list[dict],
    *,
    style: str = "apa",
    fmt=formatter.plain,
    validate: bool = False,
) -> list[str]:
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


def render_bibtex(csl_json: list[dict]) -> str:
    parts = render_citation(csl_json, style="bibtex", fmt=formatter.plain, validate=False)
    return "\n\n".join(p.strip() for p in parts if p and str(p).strip())
