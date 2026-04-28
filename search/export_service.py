"""Parsing, validation, and shared export helpers."""

import json
from dataclasses import dataclass
from typing import Optional

from django.utils.translation import gettext as _

from .csv_export import stream_csv
from .citation.constants import CITATION_EXPORT_FORMATS

class BadRequestError(Exception):
    """Client-side validation error surfaced as a JSON response by views."""

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
        raise BadRequestError(_("Invalid JSON body."))
    if not isinstance(data, dict):
        raise BadRequestError(_("Invalid payload."))
    return data


def _accept_language(request):
    header = request.META.get("HTTP_ACCEPT_LANGUAGE")
    if not header:
        return None
    part = header.split(",")[0].strip().split(";")[0].strip()
    return part or None


def _validate_document_entry(entry, index):
    if not isinstance(entry, dict):
        raise BadRequestError(_(f"Invalid document entry at index {index}."))
    if not isinstance(entry.get("source"), dict):
        raise BadRequestError(_("Each document must have a source object."))


def _validate_documents(body):
    documents = body.get("documents")
    if not isinstance(documents, list) or not documents:
        raise BadRequestError(_("Field documents must be a non-empty list."))
    for i, entry in enumerate(documents):
        _validate_document_entry(entry, i)
    return documents


def _resolve_language(body, request):
    return body.get("language_code") or _accept_language(request)


def extract_export_inputs(body, request):
    fmt = body.get("format")
    if fmt not in CITATION_EXPORT_FORMATS:
        raise BadRequestError(_("Unsupported export format."))
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


def build_csv_file(inputs):
    """Return ``(content_iterable, mime_type, file_extension)`` for CSV export."""
    return stream_csv(inputs.documents, language=inputs.language_code), "text/csv", "csv"
