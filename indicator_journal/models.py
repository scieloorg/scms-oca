import json
from django.db import models
from django.urls import reverse
from django.utils.translation import get_language
from django.utils.translation import gettext_lazy as _, gettext as translate
from wagtail.admin.panels import FieldPanel
from wagtail.fields import RichTextField
from wagtail.models import Page

from indicator.filters import clean_filters
from indicator_journal.forms import build_config_fields
from indicator_journal.metrics.config import JournalMetricConfig, JournalMetricConfigError
from indicator_journal.metrics.engine import JournalMetricEngine
from indicator_journal.navigation import get_indicator_nav_urls, get_journal_profile_url
from search_gateway.filter_ui import render_filter_sidebar
from search_gateway.freshness import get_index_freshness
from search_gateway.service import SearchGatewayService


class IndicatorPage(Page):
    is_creatable = False

    data_source = models.ForeignKey(
        "search_gateway.DataSource",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text=_("Fonte de dados do OpenSearch vinculada a este indicador."),
    )
    intro = RichTextField(blank=True, help_text=_("Texto de introdução."))

    content_panels = Page.content_panels + [
        FieldPanel("data_source"),
        FieldPanel("intro"),
    ]


class IndicatorByCategoryPage(IndicatorPage):
    content_panels = IndicatorPage.content_panels

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        if not self.data_source:
            context["error"] = translate("Data source not configured for this page.")
            return context

        data_source_name = self.data_source.index_name
        request_filters = request.POST if request.method == "POST" else request.GET
        config = JournalMetricConfig(self.data_source)
        thematic_form_key = config.form_key("thematic")
        nav_urls = get_indicator_nav_urls(self, IndicatorByCategoryPage, IndicatorGlobalPage)
        analysis_unit_options = config.analysis_units(nav_urls, current_value=data_source_name)
        engine = JournalMetricEngine(self.data_source)

        form_filters = dict(request_filters.items())
        if not form_filters.get("category_level"):
            form_filters["category_level"] = engine.get_required_field_default("category_level")

        applied_filters = clean_filters(dict(form_filters))
        applied_filters["category_level"] = form_filters["category_level"]
        applied_filters["minimum_publications"] = str(
            int(form_filters.get("minimum_publications") or engine.get_required_field_default("minimum_publications"))
        )

        field_settings = self.data_source.get_field_settings_dict()
        filter_fields_to_load = {
            field.field_name
            for field in self.data_source.get_ordered_fields(form_key=thematic_form_key)
            if field.kind == "index" and not field.hidden_in_form
        }
        exclude_fields = [n for n in field_settings if n not in filter_fields_to_load]
        filters_data, filters_error = SearchGatewayService(
            index_name=data_source_name
        ).get_filters_data(exclude_fields=exclude_fields)

        ranking_data, error = engine.get_thematic_ranking(form_filters)

        context.update({
            "data_source": data_source_name,
            "data_source_display_name": self.data_source.display_name,
            "applied_filters": applied_filters,
            "study_unit": data_source_name,
            "indicator_has_study_unit_control": bool(analysis_unit_options),
            "analysis_unit_options": analysis_unit_options,
            "filters_data": filters_data or {},
            "ranking_data": ranking_data,
            "content_updated_date": get_index_freshness(data_source_name),
        })
        context.update(nav_urls)

        if error:
            context["error"] = translate("Error executing search: %s") % error
        if filters_error:
            context["filters_error"] = translate("Error loading filters: %s") % filters_error

        if ranking_data and ranking_data.get("year") and "publication_year" not in applied_filters:
            context["applied_filters"]["publication_year"] = str(ranking_data["year"])

        context.update(
            engine.presentation.build_ranking_context(
                applied_filters,
                ranking_data,
                profile_base_url=get_journal_profile_url(JournalProfilePage, get_language()),
            )
        )
        context["applied_filters_json"] = json.dumps(context["applied_filters"])

        config_fields = build_config_fields(self.data_source, thematic_form_key, context["applied_filters"])
        context["indicator_config_fields"] = config_fields
        context["indicator_config_form_id"] = "journal-metrics-filter-form"
        context["indicator_config_submit_label"] = translate("APPLY")

        exclude_names = [str(f.get("name") or "").strip() for f in config_fields if str(f.get("name") or "").strip()]
        sidebar_payload = render_filter_sidebar(
            request,
            data_source=self.data_source,
            form_key=thematic_form_key,
            applied_filters=context["applied_filters"],
            exclude_fields=exclude_names,
            sidebar_form_id="journal-metrics-filter-form",
            sidebar_form_method="get",
            sidebar_form_action=request.path,
            submit_id="menu-submit-journal-metrics",
            reset_id="menu-reset-journal-metrics",
            reset_type="button",
        )
        context["indicator_sidebar_html"] = sidebar_payload["form_html"]

        return context


class IndicatorGlobalPage(IndicatorPage):
    content_panels = IndicatorPage.content_panels

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        if not self.data_source:
            context["error"] = translate("Data source not configured for this page.")
            return context

        data_source_name = self.data_source.index_name
        request_filters = request.POST if request.method == "POST" else request.GET
        config = JournalMetricConfig(self.data_source)
        global_form_key = config.form_key("global")
        nav_urls = get_indicator_nav_urls(self, IndicatorByCategoryPage, IndicatorGlobalPage)
        analysis_unit_options = config.analysis_units(nav_urls, current_value=data_source_name)

        engine = JournalMetricEngine(self.data_source)
        ranking_data, applied_filters = engine.get_global_ranking(request_filters)

        field_settings = self.data_source.get_field_settings_dict()
        filter_fields_to_load = {
            field.field_name
            for field in self.data_source.get_ordered_fields(form_key=global_form_key)
            if field.kind == "index" and not field.hidden_in_form
        }
        exclude_fields = [n for n in field_settings if n not in filter_fields_to_load]

        filters_data, filters_error = SearchGatewayService(
            index_name=data_source_name
        ).get_filters_data(exclude_fields=exclude_fields)

        config_fields = build_config_fields(self.data_source, global_form_key, applied_filters)
        exclude_names = [str(f.get("name") or "").strip() for f in config_fields if str(f.get("name") or "").strip()]

        sidebar_payload = render_filter_sidebar(
            request,
            data_source=self.data_source,
            form_key=global_form_key,
            applied_filters=applied_filters,
            exclude_fields=exclude_names,
            sidebar_form_id="global-metrics-filter-form",
            sidebar_form_method="get",
            sidebar_form_action=request.path,
            submit_id="menu-submit-global-metrics",
            reset_id="menu-reset-global-metrics",
            reset_type="button",
        )

        context.update({
            "data_source": data_source_name,
            "data_source_display_name": self.data_source.display_name,
            "is_global_metrics": True,
            "indicator_has_study_unit_control": bool(analysis_unit_options),
            "study_unit": data_source_name,
            "analysis_unit_options": analysis_unit_options,
            "applied_filters": applied_filters,
            "applied_filters_json": json.dumps(applied_filters),
            "filters_data": filters_data or {},
            "ranking_data": ranking_data,
            "indicator_sidebar_html": sidebar_payload["form_html"],
            "indicator_config_fields": config_fields,
            "indicator_config_form_id": "global-metrics-filter-form",
            "indicator_config_submit_label": translate("APPLY"),
            "content_updated_date": get_index_freshness(data_source_name),
        })
        context.update(nav_urls)
        context.update(
            engine.presentation.build_ranking_context(
                applied_filters,
                ranking_data,
                profile_base_url=get_journal_profile_url(JournalProfilePage, get_language()),
            )
        )

        if filters_error:
            context["filters_error"] = translate("Error loading filters: %s") % filters_error

        return context


class JournalProfilePage(Page):
    template = "indicator_journal/journal_profile_page.html"

    data_source = models.ForeignKey(
        "search_gateway.DataSource",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text=_("DataSource with journal metrics."),
    )

    show_global_metrics = models.BooleanField(
        default=False,
        help_text=_("Enable the Global Metrics tab on the profile page. Only turn on when the global index is ready."),
    )

    content_panels = Page.content_panels + [
        FieldPanel("data_source"),
        FieldPanel("show_global_metrics"),
    ]

    parent_page_types = ["IndicatorByCategoryPage"]
    subpage_types = []

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        if not self.data_source:
            context["error"] = translate("Data source not configured.")
            return context

        params = request.GET
        issn = str(params.get("journal") or params.get("issn") or "").strip()
        if not issn:
            context["error"] = translate("Missing journal identifier (ISSN).")
            return context

        selected_category_level = str(params.get("category_level") or "").strip()
        selected_category_id = str(params.get("category_id") or "").strip()
        selected_publication_year = str(params.get("publication_year") or "").strip()
        config = JournalMetricConfig(self.data_source)

        passthrough_filters = {
            key: str(params.get(key) or "").strip()
            for key in config.passthrough_params()
            if str(params.get(key) or "").strip()
        }

        profile_error = None
        filters_error = None
        filters_data = {}

        try:
            filters_data, filters_error = SearchGatewayService(
                index_name=self.data_source.index_name,
            ).get_filters_data()
        except Exception as exc:
            filters_error = str(exc)

        engine = JournalMetricEngine(self.data_source)
        profile_data = None
        global_snapshot = None

        try:
            profile_data, search_error = engine.get_profile_timeseries(
                issn=issn,
                category_level=selected_category_level,
                category_id=selected_category_id,
                publication_year=selected_publication_year,
            )
            if search_error:
                profile_error = search_error
        except Exception as exc:
            profile_error = str(exc)

        if self.show_global_metrics:
            try:
                global_snapshot = engine.fetch_global_snapshot(issn, profile_data=profile_data)
            except (JournalMetricConfigError, ValueError) as exc:
                profile_error = str(exc)

        profile_context = engine.presentation.build_profile_context(
            journal_issn=issn,
            profile_data=profile_data,
            selected_category_level=selected_category_level,
            selected_category_id=selected_category_id,
            selected_publication_year=selected_publication_year,
            passthrough_filters=passthrough_filters,
            filters_data=filters_data,
            filters_error=filters_error,
            profile_error=profile_error,
            global_snapshot=global_snapshot,
        )

        context.update(profile_context)
        context["profile_form_action"] = request.path
        context["profile_timeseries_url"] = reverse("indicator_journal:profile_options")
        context["profile_data_source"] = self.data_source.index_name
        return context

    class Meta:
        verbose_name = _("Journal Profile Page")
        verbose_name_plural = _("Journal Profile Pages")
