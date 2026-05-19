import logging
import uuid
from pathlib import Path

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.core.files.storage import default_storage
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.text import get_valid_filename
from django.utils.translation import gettext as _
from wagtail.admin import messages

from .forms import HarvestOpenSearchUploadForm
from .tasks import import_harvest_upload_opensearch

logger = logging.getLogger(__name__)


@staff_member_required
def upload_opensearch_view(request):
    index_name = settings.HARVEST_UPLOAD_OPENSEARCH_INDEX
    chunk_size = settings.HARVEST_UPLOAD_BULK_CHUNK_SIZE

    if request.method == "POST":
        form = HarvestOpenSearchUploadForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                uploaded_file = form.cleaned_data["file"]
                storage_path = _save_upload_for_task(uploaded_file)
                result = import_harvest_upload_opensearch.delay(
                    storage_path,
                    uploaded_file.name,
                    index_name=index_name,
                    chunk_size=chunk_size,
                )
            except Exception as exc:
                logger.exception("Erro ao enfileirar upload harvest para OpenSearch.")
                messages.error(
                    request,
                    _(f"Erro inesperado ao enfileirar arquivo: {exc}")
                )
            else:
                messages.success(
                    request,
                    _(
                        f"Upload enfileirado para indexação em {index_name}. "
                        f"Tarefa: {result.id}. Bulk: {chunk_size} documentos."
                    ),
                )
            return redirect(reverse("harvest_upload_opensearch"))
    else:
        form = HarvestOpenSearchUploadForm()

    return TemplateResponse(
        request,
        "harvest/upload_opensearch.html",
        {
            "form": form,
            "index_name": index_name,
            "chunk_size": chunk_size,
        },
    )


def _save_upload_for_task(uploaded_file):
    filename = get_valid_filename(Path(uploaded_file.name).name)
    storage_path = f"harvest_uploads/{uuid.uuid4()}_{filename}"
    return default_storage.save(storage_path, uploaded_file)
