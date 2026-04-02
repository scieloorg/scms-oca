import logging

from django.http import HttpResponse, JsonResponse
from django.utils.translation import gettext as _
from django.views.decorators.http import require_GET, require_POST

from .citation_constants import CITATION_EXPORT_FORMATS
from .citation_export_service import (
    CitationExportBadRequest,
    build_citation_file,
    decode_request_json,
    extract_export_inputs,
)

logger = logging.getLogger(__name__)


def _json_error(message, *, status=400, **extra):
    payload = {"error": message}
    payload.update(extra)
    return JsonResponse(payload, status=status)


def _citation_attachment_response(content, mime, ext):
    filename = f"citations.{ext}"
    response = HttpResponse(content.encode("utf-8"), content_type=f"{mime}; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@require_GET
def citation_formats_view(request):
    formats = [
        {"id": key, "label": str(label)}
        for key, label in CITATION_EXPORT_FORMATS.items()
    ]
    return JsonResponse({"formats": formats})


@require_POST
def citation_export_view(request):
    try:
        body = decode_request_json(request.body)
        inputs = extract_export_inputs(body, request)
        content, mime, ext = build_citation_file(inputs)
    except CitationExportBadRequest as err:
        return _json_error(err.message, status=err.status, **err.extra)
    except FileNotFoundError:
        logger.exception("CSL style not found during citation export")
        return _json_error(
            _("Citation style is not available on the server."),
            status=500,
        )
    except Exception:
        logger.exception("Citation export failed")
        return _json_error(_("Citation export failed."), status=500)

    return _citation_attachment_response(content, mime, ext)
