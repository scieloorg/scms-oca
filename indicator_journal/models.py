from django.db import models
from django.utils.translation import gettext_lazy as _
from wagtail.admin.panels import FieldPanel
from wagtail.fields import RichTextField
from wagtail.models import Page

from .services.category import CategoryMetricsService
from .services.global_metrics import GlobalMetricsService


class IndicatorPage(Page):
    """Abstract base for all indicator pages; provides a shared data_source FK and intro field."""

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
    """Indicator page that displays either a journal-metrics ranking or a legacy chart view."""

    default_category_level = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text=_("Ex: field, subfield, topic, domain"),
    )
    default_publication_year = models.CharField(
        max_length=4,
        blank=True,
        null=True,
        help_text=_("Ano de publicação padrão (ex: 2024)"),
    )
    default_ranking_metric = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text=_("Métrica de ranking padrão"),
    )

    content_panels = IndicatorPage.content_panels + [
        FieldPanel("default_category_level"),
        FieldPanel("default_publication_year"),
        FieldPanel("default_ranking_metric"),
    ]

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        context.update(CategoryMetricsService(self, request).get_context_data())
        return context


class IndicatorGlobalPage(IndicatorPage):
    """Indicator page that displays the global journal-metrics ranking."""

    content_panels = IndicatorPage.content_panels

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        context.update(GlobalMetricsService(self, request).get_context_data())
        return context
