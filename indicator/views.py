import json

from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.utils.translation import gettext as _
from django.views.decorators.http import require_GET, require_POST
from wagtail_modeladmin.views import CreateView, EditView

from core import tasks
from core_settings.models import Moderation
from search_gateway import data_sources_with_settings
from search_gateway.controller import get_filters_data

from .search import controller, utils
from .permission_helper import IndicatorPermissionHelper

JOURNAL_METRICS_NON_FILTER_KEYS = {"scope", "return_study_unit", "study_unit"}


@require_POST
def data_view(request):
    data_source_name = request.GET.get("data_source")
    if not data_source_name:
        return JsonResponse({"error": "Missing data_source parameter"}, status=400)

    body_text = request.body.decode()
    payload = json.loads(body_text) if body_text else {}
    filters = payload.get("filters", {})
    study_unit = payload.get("study_unit") or request.GET.get("study_unit") or "document"

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

    context = {
        "data_source": data_source_name,
        "data_source_display_name": data_source.get("display_name"),
        "applied_filters": cleaned_filters,
        "study_unit": request.GET.get("study_unit", "document"),
    }

    context["applied_filters_json"] = json.dumps(context["applied_filters"])

    return render(request, "indicator.html", context)


def journal_metrics_view(request):
    data_source_name = "journal_metrics"
    data_source = data_sources_with_settings.get_data_source(data_source_name)

    cleaned_get_filters = utils.clean_form_filters(request.GET.dict())
    for key in JOURNAL_METRICS_NON_FILTER_KEYS:
        cleaned_get_filters.pop(key, None)

    if "year" in cleaned_get_filters and "publication_year" not in cleaned_get_filters:
        cleaned_get_filters["publication_year"] = cleaned_get_filters.pop("year")

    if not str(cleaned_get_filters.get("category_level") or "").strip():
        cleaned_get_filters["category_level"] = controller.DEFAULT_JOURNAL_METRICS_CATEGORY_LEVEL

    context = {
        "data_source": data_source_name,
        "data_source_display_name": data_source.get("display_name"),
        "applied_filters": cleaned_get_filters,
        "study_unit": "journal_metrics",
    }

    field_settings = data_sources_with_settings.get_field_settings(data_source_name)
    filter_fields_to_load = {"country", "collection", "category_level", "publication_year"}

    exclude_fields = [name for name in field_settings.keys() if name not in filter_fields_to_load]

    filters_data, filters_error = get_filters_data(data_source_name, exclude_fields=exclude_fields)
    context["filters_data"] = filters_data or {}

    if filters_error:
        context["error"] = _("Error loading filters: %s") % filters_error

    default_publication_year = controller.DEFAULT_JOURNAL_METRICS_PUBLICATION_YEAR
    context["default_publication_year"] = default_publication_year

    form_filters = request.POST.dict() if request.method == "POST" else request.GET.dict()
    for key in JOURNAL_METRICS_NON_FILTER_KEYS:
        form_filters.pop(key, None)
    if not str(form_filters.get("category_level") or "").strip():
        form_filters["category_level"] = controller.DEFAULT_JOURNAL_METRICS_CATEGORY_LEVEL

    cleaned_form_filters = utils.clean_form_filters(form_filters.copy())
    for key in JOURNAL_METRICS_NON_FILTER_KEYS:
        cleaned_form_filters.pop(key, None)
    if "year" in cleaned_form_filters and "publication_year" not in cleaned_form_filters:
        cleaned_form_filters["publication_year"] = cleaned_form_filters.pop("year")

    if not str(cleaned_form_filters.get("category_level") or "").strip():
        cleaned_form_filters["category_level"] = controller.DEFAULT_JOURNAL_METRICS_CATEGORY_LEVEL
    context["applied_filters"].update(cleaned_form_filters)

    ranking_data, error = controller.get_journal_metrics_data(form_filters)

    if error:
        context["error"] = _("Error executing search: %s") % error
    else:
        context["ranking_data"] = ranking_data

        if ranking_data and ranking_data.get("year") and "publication_year" not in context["applied_filters"]:
            context["applied_filters"]["publication_year"] = str(ranking_data.get("year"))

    if default_publication_year and "publication_year" not in context["applied_filters"]:
        context["applied_filters"]["publication_year"] = default_publication_year

    context["applied_filters_json"] = json.dumps(context["applied_filters"])

    return render(request, "indicator.html", context)


@require_GET
def journal_metrics_timeseries_view(request):
    issn = request.GET.get("issn") or request.GET.get("journal_issn")
    journal = request.GET.get("journal") or request.GET.get("journal_title")
    category_id = request.GET.get("category_id")
    category_level = request.GET.get("category_level")
    publication_year = request.GET.get("publication_year")
    
    form_filters = request.GET.dict()
    
    for key in (
        "issn",
        "journal",
        "journal_issn",
        "journal_title",
        "category_id",
        "category_level",
        "publication_year",
        "scope",
        "return_study_unit",
        "study_unit",
    ):
        form_filters.pop(key, None)

    data, error = controller.get_journal_metrics_timeseries(
        issn=issn,
        journal=journal,
        category_id=category_id,
        category_level=category_level,
        publication_year=publication_year,
        form_filters=form_filters,
    )

    if error:
        status_code = 503 if error == "Service unavailable" else 404 if error == "Not found" else 400
        return JsonResponse({"error": error}, status=status_code)

    return JsonResponse(data)


@require_GET
def periodical_timeseries_view(request):
    """Time series for a single periodical using the *documents* indices.

    Example:
      /indicators/periodical/timeseries/?data_source=scientific&field_name=issn&value=1234-5678
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
