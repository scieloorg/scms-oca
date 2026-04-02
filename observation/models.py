import logging

from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _
from modelcluster.fields import ParentalKey
from wagtail.admin.panels import FieldPanel, InlinePanel
from wagtail.models import Orderable, Page

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
        InlinePanel("dimensions", label=_("Dimensions")),
    ]

    def _translation_observation_pages(self):
        candidates = []
        for page in self.get_translations(inclusive=True).specific():
            if isinstance(page, ObservationPage):
                candidates.append(page)
        return candidates

    def _effective_data_source(self):
        if self.data_source:
            return self.data_source
        for page in self._translation_observation_pages():
            if page.id == self.id:
                continue
            if page.data_source:
                return page.data_source
        return None

    def _fallback_dimension(self):
        return {
            "slug": "documents-by-country",
            "menu_label": _("Evolution of Scientific Production - World - number of documents by Country"),
            "row_field_name": "country",
            "col_field_name": "publication_year",
            "row_bucket_size": 500,
            "col_bucket_size": 300,
            "table_title": _("Evolution of Scientific Production - World - number of documents by Year"),
            "kpi_label": _("Documents"),
            "row_label": _("Country"),
            "col_label": _("Year"),
            "value_label": _("Documents"),
        }

    def _serialize_dimensions(self, source_page):
        dimensions = []
        for item in source_page.dimensions.all():
            dimensions.append(
                {
                    "slug": item.slug,
                    "menu_label": item.menu_label,
                    "row_field_name": item.row_field_name,
                    "col_field_name": item.col_field_name,
                    "row_bucket_size": item.row_bucket_size,
                    "col_bucket_size": item.col_bucket_size,
                    "table_title": item.table_title,
                    "kpi_label": item.kpi_label,
                    "row_label": item.row_label,
                    "col_label": item.col_label,
                    "value_label": item.value_label,
                    "is_default": item.is_default,
                }
            )
        return dimensions

    def get_dimensions_config(self):
        dimensions = self._serialize_dimensions(self)
        if dimensions:
            return dimensions
        for page in self._translation_observation_pages():
            if page.id == self.id:
                continue
            dimensions = self._serialize_dimensions(page)
            if dimensions:
                return dimensions
        return [self._fallback_dimension()]

    def get_default_dimension_config(self):
        dimensions = self.get_dimensions_config()
        for item in dimensions:
            if item.get("is_default"):
                return item
        return dimensions[0]

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        form_key = OBSERVATION_SEARCH_FORM_KEY
        data_source = self._effective_data_source()
        dimensions = self.get_dimensions_config()
        default_dimension = self.get_default_dimension_config()

        context.update(
            {
                "search_sidebar_html": "",
                "filters": {},
                "filter_metadata": {},
                "search_clauses": SearchPage.query_clauses(request),
                "search_query": request.GET.get("search", ""),
                "index_name": "",
                "searchable_fields": _observation_searchable_fields(data_source),
                "observation_page_id": self.id,
                "observation_dimensions": dimensions,
                "observation_default_dimension": default_dimension,
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
                    "observation_page_id": self.id,
                    "observation_dimensions": dimensions,
                    "observation_default_dimension": default_dimension,
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


class ObservationDimension(Orderable):
    page = ParentalKey(
        ObservationPage,
        on_delete=models.CASCADE,
        related_name="dimensions",
    )
    slug = models.SlugField(
        max_length=80,
        verbose_name=_("Slug"),
        help_text=_("Unique identifier for this dimension in this page."),
    )
    menu_label = models.CharField(
        max_length=255,
        verbose_name=_("Menu label"),
        help_text=_("Label shown in the dimension selector above the table."),
    )
    row_field_name = models.CharField(
        max_length=100,
        verbose_name=_("Row field name"),
        help_text=_("DataSource field key used as row dimension (e.g. country, institution)."),
    )
    col_field_name = models.CharField(
        max_length=100,
        default="publication_year",
        verbose_name=_("Column field name"),
        help_text=_("DataSource field key used as column dimension."),
    )
    row_bucket_size = models.PositiveIntegerField(default=500, verbose_name=_("Row bucket size"))
    col_bucket_size = models.PositiveIntegerField(default=300, verbose_name=_("Column bucket size"))
    table_title = models.CharField(max_length=255, verbose_name=_("Table title"))
    kpi_label = models.CharField(max_length=100, default="Documents", verbose_name=_("KPI label"))
    row_label = models.CharField(max_length=100, default="Country", verbose_name=_("Row label"))
    col_label = models.CharField(max_length=100, default="Year", verbose_name=_("Column label"))
    value_label = models.CharField(max_length=100, default="Documents", verbose_name=_("Value label"))
    is_default = models.BooleanField(
        default=False,
        verbose_name=_("Default dimension"),
        help_text=_("If checked, this dimension is selected when the page loads."),
    )

    panels = [
        FieldPanel("slug"),
        FieldPanel("menu_label"),
        FieldPanel("row_field_name"),
        FieldPanel("col_field_name"),
        FieldPanel("row_bucket_size"),
        FieldPanel("col_bucket_size"),
        FieldPanel("table_title"),
        FieldPanel("kpi_label"),
        FieldPanel("row_label"),
        FieldPanel("col_label"),
        FieldPanel("value_label"),
        FieldPanel("is_default"),
    ]

    class Meta:
        verbose_name = _("Observation dimension")
        verbose_name_plural = _("Observation dimensions")
        constraints = [
            models.UniqueConstraint(
                fields=["page", "slug"],
                name="observation_dimension_unique_slug_per_page",
            ),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.menu_label)[:80] or "dimension"
        super().save(*args, **kwargs)
