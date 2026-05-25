"""Citation-specific export and rendering helpers (RIS/BibTeX/custom styles)."""

from django.utils.translation import gettext as _

from ..export_service import BadRequestError
from ..ris_export import render_ris_lines
from .constants import CITATION_PRESET_STYLES
from .render import build_citation_items, render_bibtex, render_citation


def _to_citation_items(inputs):
    citation_items = build_citation_items(
        inputs.documents,
        language=inputs.language_code,
    )
    if len(citation_items) != len(inputs.documents):
        raise BadRequestError(_("Could not map documents to citations."))
    return citation_items


def _render_bib(inputs):
    content = render_bibtex(_to_citation_items(inputs))
    if not content.strip():
        raise BadRequestError(
            _("Could not generate BibTeX for the selection."),
            status=422,
        )
    return content, "application/x-bibtex", "bib"


def _render_ris(inputs):
    content = render_ris_lines(_to_citation_items(inputs))
    return content, "application/x-research-info-systems", "ris"


_EXPORT_RENDERERS = {
    "bib": _render_bib,
    "ris": _render_ris,
}


def build_citation_file(inputs):
    """Return ``(content, mime_type, file_extension)`` for RIS/BibTeX."""
    renderer = _EXPORT_RENDERERS.get(inputs.format_key)
    if not renderer:
        raise BadRequestError(_("Unsupported export format."))
    return renderer(inputs)


def _render_style(csl_json, style):
    rendered = render_citation(csl_json, style=style, validate=False)
    return "\n\n".join(r.strip() for r in rendered if r and r.strip())


def _render_items_style(citation_items, style):
    return _render_style(citation_items, style)


def _build_presets(citation_items):
    return [
        {
            "id": style_id,
            "label": str(label),
            "citation": _render_items_style(citation_items, style_id),
        }
        for style_id, label in CITATION_PRESET_STYLES.items()
    ]


def build_citation_preview(inputs):
    """Citação predefinida (vancouver e apa)."""
    citation_items = _to_citation_items(inputs)
    return {"presets": _build_presets(citation_items)}


def build_custom_citation(inputs, style):
    """Constroi citação baseado no input do usuário."""
    citation_items = _to_citation_items(inputs)
    return {"id": style, "citation": _render_items_style(citation_items, style)}
