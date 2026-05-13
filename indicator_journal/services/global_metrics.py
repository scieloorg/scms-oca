import json

from django.utils.translation import gettext as _

from search_gateway.filter_ui import render_filter_sidebar
from search_gateway.service import SearchGatewayService
from indicator_journal.search.controller import get_global_journal_metrics_data


class GlobalMetricsService:
    """
    Builds the template context for IndicatorGlobalPage.

    Coordinates data fetching by calling the local search controller.
    """

    FORM_KEY = "journal_metrics_global"

    def __init__(self, page, request):
        self.page = page
        self.request = request
        self.data_source = page.data_source

    def get_context_data(self):
        if not self.data_source:
            return {"error": _("Data source not configured for this page.")}

        data_source_name = self.data_source.index_name
        request_filters = self.request.POST if self.request.method == "POST" else self.request.GET

        ranking_data, applied_filters = get_global_journal_metrics_data(
            data_source_name,
            request_filters
        )

        field_settings = self.data_source.get_field_settings_dict()
        filter_fields_to_load = {"country", "collection", "publication_year"}
        exclude_fields = [n for n in field_settings if n not in filter_fields_to_load]

        filters_data, filters_error = SearchGatewayService(
            index_name=data_source_name
        ).get_filters_data(exclude_fields=exclude_fields)

        sidebar_payload = render_filter_sidebar(
            self.request,
            data_source=self.data_source,
            form_key=self.FORM_KEY,
            applied_filters=applied_filters,
            sidebar_form_id="global-metrics-filter-form",
            sidebar_form_method="get",
            sidebar_form_action=self.request.path,
            submit_id="menu-submit-global-metrics",
            reset_id="menu-reset-global-metrics",
            reset_type="reset",
        )

        context = {
            "data_source": data_source_name,
            "data_source_display_name": self.data_source.display_name,
            "is_global_metrics": True,
            "is_journal_metrics": False,
            "applied_filters": applied_filters,
            "applied_filters_json": json.dumps(applied_filters),
            "filters_data": filters_data or {},
            "ranking_data": ranking_data,
            "indicator_sidebar_html": sidebar_payload["form_html"],
        }

        if filters_error:
            context["filters_error"] = _("Error loading filters: %s") % filters_error

        return context
