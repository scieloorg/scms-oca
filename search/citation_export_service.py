"""
Parsing, validation, and file generation for citation export (BibTeX / RIS).
"""

import json
import logging
from dataclasses import dataclass
from django.conf import settings
from django.utils.translation import gettext as _

from .citation_constants import CITATION_EXPORT_FORMATS, CITATION_EXPORT_MAX_DOCUMENTS
from .citeproc_render import render_bibtex
from .csl_json import documents_payload_to_csl_json
from .ris_export import render_ris_lines

logger = logging.getLogger(__name__)


class CitationExportBadRequest(Exception):
    """Client error: use ``message``, ``status``, and optional ``extra`` for JsonResponse."""

    def __init__(
        self,
        message,
        *,
        status=400,
        extra=None,
    ):
        super().__init__(message)
        self.message = message
        self.status = status
        self.extra = extra or {}


@dataclass(frozen=True)
class CitationExportInputs:
    format_key: str
    documents: list
    language_code: str or None


def http_accept_language(request):
    al = request.META.get("HTTP_ACCEPT_LANGUAGE")
    if not al:
        return None
    part = al.split(",")[0].strip().split(";")[0].strip()
    return part or None


def decode_request_json(raw):
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise CitationExportBadRequest(_("Invalid JSON body."))
    if not isinstance(data, dict):
        raise CitationExportBadRequest(_("Invalid payload."))
    return data


def effective_max_documents():
    raw = getattr(settings, "CITATION_EXPORT_MAX_DOCUMENTS", CITATION_EXPORT_MAX_DOCUMENTS)
    try:
        n = int(raw)
    except (TypeError, ValueError):
        n = CITATION_EXPORT_MAX_DOCUMENTS
    return max(1, min(n, 500))


def extract_export_inputs(body, request):
    fmt = body.get("format")
    if fmt not in CITATION_EXPORT_FORMATS:
        raise CitationExportBadRequest(_("Unsupported export format."))

    documents = body.get("documents")
    if not isinstance(documents, list) or not documents:
        raise CitationExportBadRequest(_("Field documents must be a non-empty list."))

    max_docs = effective_max_documents()
    if len(documents) > max_docs:
        raise CitationExportBadRequest(
            _("Too many documents in one request."),
            extra={"max_documents": max_docs},
        )

    for i, entry in enumerate(documents):
        if not isinstance(entry, dict):
            raise CitationExportBadRequest(
                _(f"Invalid document entry at index {i}."),
            )
        if entry.get("id") is None:
            raise CitationExportBadRequest(_("Each document must have an id."))
        if not isinstance(entry.get("source"), dict):
            raise CitationExportBadRequest(_("Each document must have a source object."))

    lang = body.get("language_code") or http_accept_language(request)
    return CitationExportInputs(format_key=fmt, documents=documents, language_code=lang)


def build_citation_file(inputs):
    """
    Returns ``(body, mime_type, file_extension)``.
    """
    csl_json = documents_payload_to_csl_json(
        inputs.documents,
        language_code=inputs.language_code,
    )
    if len(csl_json) != len(inputs.documents):
        raise CitationExportBadRequest(_("Could not map documents to citations."))

    if inputs.format_key == "bib":
        content = render_bibtex(csl_json)
        if not content.strip():
            raise CitationExportBadRequest(
                _("Could not generate BibTeX for the selection."),
                status=422,
            )
        return content, "application/x-bibtex", "bib"

    if inputs.format_key == "ris":
        content = render_ris_lines(csl_json)
        return content, "application/x-research-info-systems", "ris"

    raise CitationExportBadRequest(_("Unsupported export format."))
