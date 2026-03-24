import json

from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.utils.translation import gettext as _
from django.views.decorators.http import require_GET, require_POST
from wagtail.views import serve as wagtail_serve
from wagtail_modeladmin.views import CreateView, EditView

from core import tasks
from core_settings.models import Moderation
from search_gateway.forms import build_data_source_form_payload
from search_gateway.forms import render_filter_sidebar
from search_gateway.models import DataSource
from search_gateway.request_filters import extract_applied_filters
from search_gateway.service import SearchGatewayService

from .journal_metrics import data_source as journal_metrics_data_source
from .journal_metrics import params as journal_metrics_params
from .journal_metrics import presentation as journal_metrics_presentation
from .search import controller as search_controller, utils
from .permission_helper import IndicatorPermissionHelper

def _collect_form_group_fields(payload, group_keys):
    selected_fields = []
    selected_names = set()
    normalized_group_keys = {str(group_key or "").strip() for group_key in (group_keys or []) if str(group_key or "").strip()}

    for group in (payload or {}).get("form_groups") or []:
        if str(group.get("key") or "").strip() not in normalized_group_keys:
            continue
        for field in group.get("fields") or []:
            field_name = str(field.get("name") or "").strip()
            if not field_name or field_name in selected_names:
                continue
            selected_names.add(field_name)
            selected_fields.append(field)

    return selected_fields


def _infer_panel_groups_from_payload(payload):
    panel_groups = []
    for group in (payload or {}).get("form_groups") or []:
        group_key = str(group.get("key") or "").strip()
        if not group_key:
            continue
        if any(str(field.get("kind") or "").strip() == "control" for field in (group.get("fields") or [])):
            panel_groups.append(group_key)
    return panel_groups


@require_GET
def root_journal_metrics_redirect_view(request):
    query_profile_issn = journal_metrics_params.get_profile_issn(request.GET)
    if query_profile_issn:
        return HttpResponseRedirect(journal_metrics_params.build_profile_url(request.GET, query_profile_issn))

    return wagtail_serve(request, "")


@require_POST
def data_view(request):
    data_source_name = request.GET.get("data_source")
    if not data_source_name:
        return JsonResponse({"error": "Missing data_source parameter"}, status=400)

    body_text = request.body.decode()
    payload = json.loads(body_text) if body_text else {}
    filters = payload.get("filters", {})
    study_unit = payload.get("study_unit") or request.GET.get("study_unit") or "document"

    data, error = search_controller.get_indicator_data(data_source_name, dict(filters), study_unit=study_unit)
    if error:
        status_code = 503 if error == "Service unavailable" else 400 if error == "Invalid data_source" else 500
        return JsonResponse({"error": error}, status=status_code)

    return JsonResponse(data)


def indicator_view(request, data_source_name):
    data_source = DataSource.get_by_index_name(index_name=data_source_name)
    if not data_source:
        return JsonResponse({"error": "Invalid data_source"}, status=404)

    applied_filters = extract_applied_filters(request.GET, data_source, form_key="indicator")
    breakdown_payload = build_data_source_form_payload(
        data_source,
        form_key="indicator",
        applied_filters=applied_filters,
        include_fields=["breakdown_variable"],
    )
    breakdown_field = None
    for group in breakdown_payload.get("form_groups") or []:
        fields = group.get("fields") or []
        if fields:
            breakdown_field = fields[0]
            break

    sidebar_payload = render_filter_sidebar(
        request,
        data_source=data_source,
        form_key="indicator",
        applied_filters=applied_filters,
        exclude_fields=["breakdown_variable"],
        sidebar_form_id="indicator-filter-form",
        sidebar_form_method="post",
        submit_label=_("FILTRAR"),
        reset_label=_("LIMPAR"),
        submit_id="menu-submit",
        reset_id="menu-reset",
        reset_type="button",
    )

    context = {
        "data_source": data_source_name,
        "data_source_display_name": data_source.display_name,
        "applied_filters": applied_filters,
        "indicator_sidebar_html": sidebar_payload["form_html"],
        "indicator_breakdown_field": breakdown_field,
        "indicator_has_study_unit_control": data_source_name != "social_production",
        "is_journal_metrics": False,
        "study_unit": request.GET.get("study_unit", "document"),
    }

    context["applied_filters_json"] = json.dumps(context["applied_filters"])

    return render(request, "indicator.html", context)


def _render_journal_metrics_profile(request, issn=None):
    journal_issn = journal_metrics_params.get_profile_issn(request.GET, issn=issn)
    if not journal_issn:
        return JsonResponse({"error": "Missing journal parameter"}, status=400)

    selected_category_level = str(request.GET.get("category_level") or "").strip()
    if not selected_category_level:
        selected_category_level = journal_metrics_data_source.get_default_category_level()

    selected_publication_year = str(request.GET.get("publication_year") or "").strip()
    if not selected_publication_year:
        selected_publication_year = str(journal_metrics_data_source.get_default_publication_year())

    selected_category_id = str(request.GET.get("category_id") or "").strip()
    profile_passthrough_filters = journal_metrics_params.extract_profile_passthrough_filters(request.GET)

    data_source = journal_metrics_data_source.get_journal_metrics_data_source()
    if not data_source:
        return JsonResponse({"error": "Invalid data_source"}, status=404)

    search_gateway_service = SearchGatewayService(index_name=journal_metrics_data_source.JOURNAL_METRICS_DATA_SOURCE)
    field_settings = data_source.get_field_settings_dict()
    filter_fields_to_load = {"category_level"}
    exclude_fields = [name for name in field_settings.keys() if name not in filter_fields_to_load]

    filters_data, filters_error = search_gateway_service.get_filters_data(exclude_fields=exclude_fields)

    profile_data, profile_error = search_controller.get_journal_metrics_timeseries(
        issn=journal_issn or None,
        journal=None,
        category_id=selected_category_id or None,
        category_level=selected_category_level,
        publication_year=selected_publication_year,
        form_filters=profile_passthrough_filters,
    )

    context = journal_metrics_presentation.build_profile_context(
        journal_issn=journal_issn,
        profile_data=profile_data,
        selected_category_level=selected_category_level,
        selected_category_id=selected_category_id,
        selected_publication_year=selected_publication_year,
        profile_passthrough_filters=profile_passthrough_filters,
        filters_data=filters_data,
        filters_error=filters_error,
        profile_error=profile_error,
    )

    return render(request, "journal_profile.html", context)


def journal_metrics_view(request):
    query_profile_issn = journal_metrics_params.get_profile_issn(request.GET)
    if request.method == "GET" and query_profile_issn:
        return _render_journal_metrics_profile(request, query_profile_issn)

    data_source_name = journal_metrics_data_source.JOURNAL_METRICS_DATA_SOURCE
    data_source = journal_metrics_data_source.get_journal_metrics_data_source()
    if not data_source:
        return JsonResponse({"error": "Invalid data_source"}, status=404)

    cleaned_get_filters = journal_metrics_params.normalize_request_filters(
        request.GET.dict(),
        source_filters=request.GET,
        clean=True,
    )

    context = {
        "data_source": data_source_name,
        "data_source_display_name": data_source.display_name,
        "applied_filters": cleaned_get_filters,
        "study_unit": journal_metrics_data_source.JOURNAL_METRICS_DATA_SOURCE,
        "default_category_id": journal_metrics_data_source.get_default_category_id(),
        "indicator_has_study_unit_control": True,
        "is_journal_metrics": True,
    }

    field_settings = data_source.get_field_settings_dict()
    filter_fields_to_load = {"country", "collection", "category_level", "publication_year"}

    exclude_fields = [name for name in field_settings.keys() if name not in filter_fields_to_load]

    search_gateway_service = SearchGatewayService(index_name=data_source_name)
    filters_data, filters_error = search_gateway_service.get_filters_data(exclude_fields=exclude_fields)
    context["filters_data"] = filters_data or {}

    if filters_error:
        context["error"] = _("Error loading filters: %s") % filters_error

    default_publication_year = journal_metrics_data_source.get_default_publication_year()
    context["default_publication_year"] = default_publication_year

    request_filters = request.POST if request.method == "POST" else request.GET
    form_filters = journal_metrics_params.normalize_request_filters(
        request_filters.dict(),
        source_filters=request_filters,
        clean=False,
    )

    cleaned_form_filters = journal_metrics_params.normalize_request_filters(
        form_filters,
        source_filters=request_filters,
        clean=True,
    )
    context["applied_filters"].update(cleaned_form_filters)

    ranking_data, error = search_controller.get_journal_metrics_data(form_filters)

    if error:
        context["error"] = _("Error executing search: %s") % error
    else:
        context["ranking_data"] = ranking_data

        if ranking_data and ranking_data.get("year") and "publication_year" not in context["applied_filters"]:
            context["applied_filters"]["publication_year"] = str(ranking_data.get("year"))

    if default_publication_year and "publication_year" not in context["applied_filters"]:
        context["applied_filters"]["publication_year"] = default_publication_year

    context.update(
        journal_metrics_presentation.build_ranking_context(
            context["applied_filters"],
            ranking_data,
        )
    )

    context["applied_filters_json"] = json.dumps(context["applied_filters"])
    configuration_payload = build_data_source_form_payload(
        data_source,
        form_key="journal_metrics",
        applied_filters=context["applied_filters"],
    )
    panel_groups = data_source.get_form_panel_groups("journal_metrics")
    if not panel_groups:
        panel_groups = _infer_panel_groups_from_payload(configuration_payload)
    context["indicator_config_fields"] = _collect_form_group_fields(configuration_payload, panel_groups)
    context["indicator_config_form_id"] = "journal-metrics-filter-form"
    context["indicator_config_submit_label"] = _("APPLY")
    config_field_names = [
        str(field.get("name") or "").strip()
        for field in context["indicator_config_fields"]
        if str(field.get("name") or "").strip()
    ]

    sidebar_payload = render_filter_sidebar(
        request,
        data_source=data_source,
        form_key="journal_metrics",
        applied_filters=context["applied_filters"],
        exclude_fields=config_field_names,
        sidebar_form_id="journal-metrics-filter-form",
        sidebar_form_method="get",
        sidebar_form_action=request.path,
        submit_label=_("FILTRAR"),
        reset_label=_("LIMPAR"),
        submit_id="menu-submit-journal-metrics",
        reset_id="menu-reset-journal-metrics",
        reset_type="reset",
    )
    context["indicator_sidebar_html"] = sidebar_payload["form_html"]

    return render(request, "indicator.html", context)

@require_GET
def journal_metrics_timeseries_view(request):
    timeseries_request = journal_metrics_params.build_timeseries_request(request.GET.dict())

    data, error = search_controller.get_journal_metrics_timeseries(
        issn=timeseries_request["issn"],
        journal=None,
        category_id=timeseries_request["category_id"],
        category_level=timeseries_request["category_level"],
        publication_year=timeseries_request["publication_year"],
        form_filters=timeseries_request["form_filters"],
    )

    if error:
        status_code = 503 if error == "Service unavailable" else 404 if error == "Not found" else 400
        return JsonResponse({"error": error}, status=status_code)

    return JsonResponse(data)


@require_GET
def periodical_timeseries_view(request):
    """Time series for a single periodical using the *documents* indices.

    Example:
      /indicators/periodical/timeseries/?data_source=scientific_production&field_name=issn&value=1234-5678
    """

    data_source_name = request.GET.get("data_source")
    field_name = request.GET.get("field_name")
    value = request.GET.get("value")

    if not data_source_name:
        return JsonResponse({"error": "Missing data_source parameter"}, status=400)

    if not field_name or not value:
        return JsonResponse({"error": "Missing field_name or value parameter"}, status=400)

    filters = {field_name: value}

    data, error = search_controller.get_indicator_data(data_source_name, filters)
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
