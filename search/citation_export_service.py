"""
Parsing, validation, and file generation for citation export and preview.
"""

import json
import logging
from dataclasses import dataclass
from typing import Optional

from django.utils.translation import gettext as _

from .citation_constants import CITATION_EXPORT_FORMATS, CITATION_PRESET_STYLES
from .citeproc_render import render_bibtex, render_citation
from .csl_json import documents_payload_to_csl_json
from .ris_export import render_ris_lines

_EXPORT_RENDERERS = {
    "bib": lambda csl: (render_bibtex(csl), "application/x-bibtex", "bib"),
    "ris": lambda csl: (render_ris_lines(csl), "application/x-research-info-systems", "ris"),
}


logger = logging.getLogger(__name__)


class CitationBadRequest(Exception):
    """Client-side error surfaced as a JSON response by the view layer."""

    def __init__(self, message, *, status=400, extra=None):
        super().__init__(message)
        self.message = message
        self.status = status
        self.extra = extra or {}

@dataclass(frozen=True)
class CitationInputs:
    documents: list
    language_code: Optional[str] = None
    format_key: Optional[str] = None


def parse_request_body(raw_body):
    try:
        data = json.loads(raw_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise CitationBadRequest(_("Invalid JSON body."))
    if not isinstance(data, dict):
        raise CitationBadRequest(_("Invalid payload."))
    return data


def _accept_language(request):
    header = request.META.get("HTTP_ACCEPT_LANGUAGE")
    if not header:
        return None
    part = header.split(",")[0].strip().split(";")[0].strip()
    return part or None


def _validate_document_entry(entry, index):
    if not isinstance(entry, dict):
        raise CitationBadRequest(_(f"Invalid document entry at index {index}."))
    if not isinstance(entry.get("source"), dict):
        raise CitationBadRequest(_("Each document must have a source object."))


def _validate_documents(body):
    documents = body.get("documents")
    if not isinstance(documents, list) or not documents:
        raise CitationBadRequest(_("Field documents must be a non-empty list."))
    for i, entry in enumerate(documents):
        _validate_document_entry(entry, i)
    return documents


def _resolve_language(body, request):
    return body.get("language_code") or _accept_language(request)


def extract_export_inputs(body, request):
    fmt = body.get("format")
    if fmt not in CITATION_EXPORT_FORMATS:
        raise CitationBadRequest(_("Unsupported export format."))
    documents = _validate_documents(body)
    return CitationInputs(
        format_key=fmt,
        documents=documents,
        language_code=_resolve_language(body, request),
    )


def extract_preview_inputs(body, request):
    documents = _validate_documents(body)
    return CitationInputs(
        documents=documents,
        language_code=_resolve_language(body, request),
    )

def _to_csl_json(inputs):
    csl_json = documents_payload_to_csl_json(
        inputs.documents,
        language_code=inputs.language_code,
    )
    if len(csl_json) != len(inputs.documents):
        raise CitationBadRequest(_("Could not map documents to citations."))
    return csl_json



def build_citation_file(inputs):
    """Return ``(content, mime_type, file_extension)``."""
    csl_json = _to_csl_json(inputs)

    renderer = _EXPORT_RENDERERS.get(inputs.format_key)
    if not renderer:
        raise CitationBadRequest(_("Unsupported export format."))

    content, mime, ext = renderer(csl_json)
    if inputs.format_key == "bib" and not content.strip():
        raise CitationBadRequest(
            _("Could not generate BibTeX for the selection."),
            status=422,
        )
    return content, mime, ext

def _render_style(csl_json, style):
    rendered = render_citation(csl_json, style=style, validate=False)
    return "\n\n".join(r.strip() for r in rendered if r and r.strip())


def set_presets_cited(csl_json):
    presets = [
        {
            "id": style_id,
            "label": str(label),
            "citation": _render_style(csl_json, style_id),
        }
        for style_id, label in CITATION_PRESET_STYLES.items()
    ]
    return presets


def build_citation_preview(inputs):
    """
    Citação predefinida (vancouver e apa)
    """
    csl_json = _to_csl_json(inputs)
    return {"presets": set_presets_cited(csl_json)}

def build_custom_citation(inputs, style):
    """
    Constroi citação baseado no input do usuário.
    """
    csl_json = _to_csl_json(inputs)
    return {"id": style, "citation": _render_style(csl_json, style)}
