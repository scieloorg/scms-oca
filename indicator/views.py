import json

from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.utils.translation import gettext as _
from django.views.decorators.http import require_GET, require_POST
from wagtail.contrib.modeladmin.views import CreateView, EditView

from core import tasks
from core_settings.models import Moderation
from search_gateway import data_sources_with_settings
from search_gateway.controller import get_filters_data

from .search import controller, utils
from .permission_helper import IndicatorPermissionHelper


@require_POST
def data_view(request):
    data_source_name = request.GET.get("data_source")
    if not data_source_name:
        return JsonResponse({"error": "Missing data_source parameter"}, status=400)

    body_text = request.body.decode()
    payload = json.loads(body_text) if body_text else {}
    filters = payload.get("filters", {})
    study_unit = payload.get("study_unit") or request.GET.get("study_unit") or "document"
    if study_unit not in ("document", "journal"):
        study_unit = "document"

    data, error = controller.get_indicator_data(data_source_name, dict(filters), study_unit=study_unit)
    if error:
        status_code = 503 if error == "Service unavailable" else 400 if error == "Invalid data_source" else 500
        return JsonResponse({"error": error}, status=status_code)

    return JsonResponse(data)


def indicator_view(request, data_source_name):
    data_source = data_sources_with_settings.get_data_source(data_source_name)
    if not data_source:
        return JsonResponse({"error": "Invalid data_source"}, status=404)

    cleaned_filters = utils.clean_form_filters(request.GET.dict())
    study_unit = request.GET.get("study_unit", "document")
    if study_unit not in ("document", "journal"):
        study_unit = "document"
    context = {
        "data_source": data_source_name,
        "data_source_display_name": data_source.get("display_name"),
        "applied_filters": cleaned_filters,
        "study_unit": study_unit,
    }
    context["applied_filters_json"] = json.dumps(context["applied_filters"])
    return render(request, "indicator.html", context)


def journal_metrics_view(request):
    data_source_name = "journal_metrics"
    data_source = data_sources_with_settings.get_data_source(data_source_name)

    cleaned_get_filters = utils.clean_form_filters(request.GET.dict())
    context = {
        "data_source": data_source_name,
        "data_source_display_name": data_source.get("display_name"),
        "applied_filters": cleaned_get_filters,
    }

    context["filters_data"], _ = get_filters_data(data_source_name)

    if request.method == "POST":
        form_filters = request.POST.dict()
        cleaned_post_filters = utils.clean_form_filters(form_filters.copy())
        context["applied_filters"].update(cleaned_post_filters)

        ranking_data, error = controller.get_journal_metrics_data(form_filters)
        if error:
            context["error"] = _("Error executing search: %s") % error
        else:
            context["ranking_data"] = ranking_data

    context["applied_filters_json"] = json.dumps(context["applied_filters"])
    return render(request, "indicator.html", context)


@require_GET
def journal_metrics_timeseries_view(request):
    issn = request.GET.get("issn")
    journal = request.GET.get("journal")

    data, error = controller.get_journal_metrics_timeseries(issn=issn, journal=journal)
    if error:
        status_code = 503 if error == "Service unavailable" else 404 if error == "Not found" else 400
        return JsonResponse({"error": error}, status=status_code)

    return JsonResponse(data)


@require_GET
def periodical_timeseries_view(request):
    """Time series for a single periodical using the *documents* indices.

    Example:
      /indicators/periodical/timeseries/?data_source=world&field_name=issn&value=1234-5678
    """

    data_source_name = request.GET.get("data_source")
    field_name = request.GET.get("field_name")
    value = request.GET.get("value")

    if not data_source_name:
        return JsonResponse({"error": "Missing data_source parameter"}, status=400)
    if not field_name or not value:
        return JsonResponse({"error": "Missing field_name or value parameter"}, status=400)

    filters = {field_name: value}
    data, error = controller.get_indicator_data(data_source_name, filters)
    if error:
        status_code = 503 if error == "Service unavailable" else 400 if error == "Invalid data_source" else 500
        return JsonResponse({"error": error}, status=status_code)

    return JsonResponse(data)


class IndicatorDirectoryEditView(EditView):
    def get_moderation(self):
        if Moderation.objects.filter(model=self.model.__name__, status=True).exists():
            return Moderation.objects.get(model=self.model.__name__)

    @property
    def must_moderate(self):
        if self.request.user.is_staff:
            return False
        return IndicatorPermissionHelper(model=self.model).must_be_moderate(self.request.user)

    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        if self.must_moderate and self.object.record_status != "PUBLISHED":
            if self.get_moderation():
                self.object.record_status = "TO MODERATE"
                self.object.save()
        return HttpResponseRedirect(self.get_success_url())


class IndicatorDirectoryCreateView(CreateView):
    def get_moderation(self):
        if Moderation.objects.filter(model=self.model.__name__, status=True).exists():
            return Moderation.objects.get(model=self.model.__name__)

    @property
    def must_moderate(self):
        if self.get_moderation():
            if self.request.user.is_staff:
                return False
            return IndicatorPermissionHelper(model=self.model).must_be_moderate(self.request.user)

    def form_valid(self, form):
        self.object = form.save_all(self.request.user)
        if self.must_moderate:
            moderation = self.get_moderation()
            if moderation:
                self.object.record_status = "TO MODERATE"
                self.object.save()
                if moderation.send_mail:
                    user_email = self.get_moderation().moderator.email or None
                    group_mails = [
                        user.email
                        for user in self.get_moderation().group_moderator.user_set.all()
                        if user.email
                    ] if self.get_moderation().group_moderator else []
                    tasks.send_mail(
                        _("Novo conteúdo para moderação - %s" % self.model._meta.verbose_name.title()),
                        render_to_string(
                            "email/moderate_email.html",
                            {"obj": self.object, "user": self.request.user, "request": self.request},
                        ),
                        to_list=[user_email],
                        bcc_list=group_mails,
                        html=True,
                    )
        return HttpResponseRedirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["has_moderation"] = self.must_moderate
        return context
