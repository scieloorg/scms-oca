import functools
import logging

from django.http import HttpResponse, JsonResponse, StreamingHttpResponse
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.http import require_GET, require_POST

from .render import list_installed_csl_styles
from .constants import CITATION_PRESET_STYLES
from .export_service import (
    build_citation_file,
    build_citation_preview,
    build_custom_citation,
)
from ..export_service import (
    BadRequestError,
    build_csv_file,
    extract_export_inputs,
    extract_preview_inputs,
    parse_request_body,
)

logger = logging.getLogger(__name__)


def _json_error(message, *, status=400, **extra):
    return JsonResponse({"error": message, **extra}, status=status)


def _file_attachment(content, mime, ext):
    resp = HttpResponse(content.encode("utf-8"), content_type=f"{mime}; charset=utf-8")
    timestamp = timezone.localtime().strftime("%Y%m%d-%H%M")
    resp["Content-Disposition"] = f'attachment; filename="citation-{timestamp}.{ext}"'
    return resp


def _streaming_file_attachment(content, mime, ext):
    resp = StreamingHttpResponse(content, content_type=f"{mime}; charset=utf-8")
    timestamp = timezone.localtime().strftime("%Y%m%d-%H%M")
    resp["Content-Disposition"] = f'attachment; filename="citation-{timestamp}.{ext}"'
    return resp


def _handle_citation_errors(view_fn):
    @functools.wraps(view_fn)
    def wrapper(request, *args, **kwargs):
        try:
            return view_fn(request, *args, **kwargs)
        except BadRequestError as err:
            return _json_error(err.message, status=err.status, **err.extra)
        except FileNotFoundError:
            logger.exception("CSL style not found")
            return _json_error(
                _("Citation style is not available on the server."),
                status=500,
            )
        except Exception:
            logger.exception("Citation operation failed")
            return _json_error(_("An unexpected error occurred."), status=500)

    return wrapper


@require_GET
def citation_csl_styles_view(request):
    preset_ids = set(CITATION_PRESET_STYLES)
    styles = [s for s in list_installed_csl_styles() if s["id"] not in preset_ids]
    return JsonResponse({"styles": styles})


@require_POST
@_handle_citation_errors
def export_view(request):
    body = parse_request_body(request.body)
    inputs = extract_export_inputs(body, request)
    if inputs.format_key == "csv":
        content, mime, ext = build_csv_file(inputs)
        return _streaming_file_attachment(content, mime, ext)
    else:
        content, mime, ext = build_citation_file(inputs)
    return _file_attachment(content, mime, ext)


@require_POST
@_handle_citation_errors
def citation_preview_view(request):
    body = parse_request_body(request.body)
    inputs = extract_preview_inputs(body, request)
    return JsonResponse(build_citation_preview(inputs))


@require_POST
@_handle_citation_errors
def citation_custom_style_view(request):
    body = parse_request_body(request.body)
    style = body.get("style", "").strip().lower()
    if not style:
        raise BadRequestError(_("Style name is required."))
    inputs = extract_preview_inputs(body, request)
    return JsonResponse(build_custom_citation(inputs, style))
