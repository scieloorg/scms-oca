import json

from django.utils.translation import gettext as _

from search_gateway.filter_ui import build_data_source_form_payload, render_filter_sidebar
from search_gateway.request_filters import extract_applied_filters
from search_gateway.service import SearchGatewayService
from indicator.journal_metrics import params as journal_metrics_params
from indicator.journal_metrics import presentation as journal_metrics_presentation
from indicator.search import controller as search_controller

from indicator_journal.services.base import infer_panel_groups_from_payload, collect_form_group_fields, get_field_names


class CategoryMetricsService:
    """
    Builds the template context for IndicatorByCategoryPage.

    Automatically selects between two rendering modes based on the page's
    data source configuration:

    * journal_metrics mode – the data source has a journal_metrics
      form (e.g. journal_metrics_by_*).  Renders a sortable ranking table.
    * indicator mode – the data source has an indicator form (e.g.
      scientific_production).  Renders the legacy chart-based view.
    """

    def __init__(self, page, request):
        self.page = page
        self.request = request
        self.data_source = page.data_source
        self.default_category_level = page.default_category_level or "field"
        self.default_publication_year = page.default_publication_year
        self.default_ranking_metric = page.default_ranking_metric

    def get_context_data(self):
        if not self.data_source:
            return {"error": _("Data source not configured for this page.")}
        if self._has_journal_metrics_form():
            return self._get_journal_metrics_context()
        return self._get_indicator_context()

    def _has_journal_metrics_form(self):
        """Return True when the data source is configured for the ranking UI."""
        try:
            return bool(self.data_source.get_form_panel_groups("journal_metrics"))
        except Exception:
            return False

    def _get_indicator_context(self):
        data_source_name = self.data_source.index_name
        request = self.request

        applied_filters = extract_applied_filters(
            request.GET, self.data_source, form_key="indicator"
        )

        breakdown_payload = build_data_source_form_payload(
            self.data_source,
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
            data_source=self.data_source,
            form_key="indicator",
            applied_filters=applied_filters,
            exclude_fields=["breakdown_variable"],
            sidebar_form_id="indicator-filter-form",
            sidebar_form_method="post",
            submit_id="menu-submit",
            reset_id="menu-reset",
            reset_type="button",
        )

        context = {
            "data_source": data_source_name,
            "data_source_display_name": self.data_source.display_name,
            "applied_filters": applied_filters,
            "indicator_sidebar_html": sidebar_payload["form_html"],
            "indicator_breakdown_field": breakdown_field,
            "indicator_has_study_unit_control": data_source_name != "social_production",
            "is_journal_metrics": False,
            "study_unit": request.GET.get("study_unit", "document"),
        }
        context["applied_filters_json"] = json.dumps(context["applied_filters"])
        return context

    def _get_journal_metrics_context(self):
        data_source_name = self.data_source.index_name
        request = self.request
        request_filters = request.POST if request.method == "POST" else request.GET

        form_filters = journal_metrics_params.normalize_request_filters(
            request_filters.dict(),
            source_filters=request_filters,
            clean=False,
        )
        if not form_filters.get("category_level"):
            form_filters["category_level"] = self.default_category_level
        if not form_filters.get("publication_year") and self.default_publication_year:
            form_filters["publication_year"] = self.default_publication_year
        if not form_filters.get("ranking_metric") and self.default_ranking_metric:
            form_filters["ranking_metric"] = self.default_ranking_metric

        applied_filters = journal_metrics_params.normalize_request_filters(
            form_filters,
            source_filters=request_filters,
            clean=True,
        ).copy()

        field_settings = self.data_source.get_field_settings_dict()
        filter_fields_to_load = {"country", "collection", "category_level", "publication_year"}
        exclude_fields = [n for n in field_settings if n not in filter_fields_to_load]
        filters_data, _ = SearchGatewayService(index_name=data_source_name).get_filters_data(
            exclude_fields=exclude_fields
        )

        ranking_data, error = search_controller.get_journal_metrics_data(form_filters)

        context = {
            "data_source": data_source_name,
            "data_source_display_name": self.data_source.display_name,
            "applied_filters": applied_filters,
            "study_unit": data_source_name,
            "is_journal_metrics": True,
            "filters_data": filters_data or {},
            "default_publication_year": self.default_publication_year,
            "ranking_data": ranking_data,
        }

        if error:
            context["error"] = _("Error executing search: %s") % error

        if ranking_data and ranking_data.get("year") and "publication_year" not in applied_filters:
            context["applied_filters"]["publication_year"] = str(ranking_data["year"])

        context.update(
            journal_metrics_presentation.build_ranking_context(applied_filters, ranking_data)
        )
        context["applied_filters_json"] = json.dumps(context["applied_filters"])

        config_payload = build_data_source_form_payload(
            self.data_source,
            form_key="journal_metrics",
            applied_filters=context["applied_filters"],
        )
        panel_groups = self.data_source.get_form_panel_groups("journal_metrics") or \
            infer_panel_groups_from_payload(config_payload)
        config_fields = collect_form_group_fields(config_payload, panel_groups)

        context["indicator_config_fields"] = config_fields
        context["indicator_config_form_id"] = "journal-metrics-filter-form"
        context["indicator_config_submit_label"] = _("APPLY")

        sidebar_payload = render_filter_sidebar(
            request,
            data_source=self.data_source,
            form_key="journal_metrics",
            applied_filters=context["applied_filters"],
            exclude_fields=get_field_names(config_fields),
            sidebar_form_id="journal-metrics-filter-form",
            sidebar_form_method="get",
            sidebar_form_action=request.path,
            submit_id="menu-submit-journal-metrics",
            reset_id="menu-reset-journal-metrics",
            reset_type="reset",
        )
        context["indicator_sidebar_html"] = sidebar_payload["form_html"]

        return context
