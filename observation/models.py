import logging

from django.db import models
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _
from wagtail.admin.panels import FieldPanel
from wagtail.models import Page

from search.models import SearchPage
from search_gateway.filter_ui import render_filter_sidebar
from search_gateway.models import DataSource
from search_gateway.request_filters import extract_applied_filters
from search_gateway.service import SearchGatewayService

logger = logging.getLogger(__name__)

OBSERVATION_SEARCH_FORM_KEY = "search"


def _observation_searchable_fields(data_source):
    if not data_source:
        return [("all", gettext("All"))]
    result = [("all", gettext("All"))]
    for field_name, cfg in (data_source.field_settings or {}).items():
        if cfg.get("settings", {}).get("support_query_operator"):
            label = cfg.get("settings", {}).get("label", field_name)
            if isinstance(label, str) and label:
                label = gettext(label)
            result.append((str(field_name), label or field_name))
    return result


class ObservationPage(Page):
    data_source = models.ForeignKey(
        DataSource,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="observation_pages",
        verbose_name=_("Data Source"),
        help_text=_("Fonte de dados OpenSearch associada a esta página de busca."),
    )

    content_panels = Page.content_panels + [
        FieldPanel("data_source"),
    ]

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        form_key = OBSERVATION_SEARCH_FORM_KEY
        data_source = self.data_source

        context.update(
            {
                "search_sidebar_html": "",
                "filters": {},
                "filter_metadata": {},
                "search_clauses": SearchPage.query_clauses(request),
                "search_query": request.GET.get("search", ""),
                "index_name": "",
                "searchable_fields": _observation_searchable_fields(data_source),
            }
        )

        if not data_source:
            logger.warning(
                "ObservationPage '%s' has no data_source configured.", self.title
            )
            return context

        service = SearchGatewayService(index_name=data_source.index_name)
        if not service.data_source:
            logger.warning(
                "ObservationPage '%s': no DataSource for index %s.",
                self.title,
                data_source.index_name,
            )
            return context

        try:
            applied_filters = extract_applied_filters(
                request.GET, data_source, form_key=form_key
            )
            sidebar_payload = render_filter_sidebar(
                request,
                data_source=data_source,
                form_key=form_key,
                applied_filters=applied_filters,
                sidebar_form_id="observation-filter-form",
                sidebar_form_method="get",
                submit_label=_("APLICAR"),
                reset_label=_("LIMPAR"),
                submit_id="observation-filter-generate",
                reset_id="observation-filter-reset",
                reset_type="button",
            )
            filters, filters_error = service.get_filters_data()
            if filters_error:
                logger.warning(
                    "ObservationPage '%s': filters unavailable: %s",
                    self.title,
                    filters_error,
                )
                filters = {}

            filter_metadata = (
                data_source.get_filter_metadata(filters, form_key=form_key)
                if filters
                else {}
            )

            context.update(
                {
                    "search_sidebar_html": sidebar_payload["form_html"],
                    "filters": filters,
                    "filter_metadata": filter_metadata,
                    "index_name": data_source.index_name,
                    "searchable_fields": _observation_searchable_fields(data_source),
                }
            )
        except Exception as exc:
            logger.warning(
                "ObservationPage '%s': error building filter context: %s",
                self.title,
                exc,
                exc_info=True,
            )

        return context
