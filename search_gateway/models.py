from django.db import models
from django.utils.translation import gettext_lazy as _
from modelcluster.models import ClusterableModel
from wagtail.admin.panels import FieldPanel, InlinePanel
from wagtail.models import ParentalKey


class DataSource(ClusterableModel):
    index_name = models.CharField(
        max_length=255,
        help_text=_("Nome do índice no OpenSearch"),
    )
    display_name = models.CharField(
        max_length=255,
        blank=True,
        help_text=_("Nome de exibição para o usuário"),
    )
    source_fields = models.JSONField(
        default=list,
        blank=True,
        help_text=_("Lista de campos retornados do ES, ex: ['_id', 'title']"),
    )

    panels = [
        FieldPanel("index_name"),
        FieldPanel("display_name"),
        FieldPanel("source_fields"),
        InlinePanel("settings_filters", label=_("Filtros")),
    ]

    class Meta:
        verbose_name = _("Data Source")
        verbose_name_plural = _("Data Sources")

    def __str__(self):
        return self.display_name or self.index_name

    def to_dict(self):
        result = {
            "index_name": self.index_name,
            "display_name": self.display_name,
            "field_settings": {
                fs.field_name: fs.to_dict()
                for fs in self.settings_filters.all()
            },
        }
        return result

    def get_field_settings_dict(self):
        return {
            fs.field_name: fs.to_dict()
            for fs in self.settings_filters.all()
        }
    
    @property
    def build_filters_query(self):
        """Build the ES aggregation query body for this data source's filters.

        Equivalent to SearchGatewayService.get_filters().
        """
        aggs = {}
        for fs in self.settings_filters.all():
            fl_size = fs.filter.get("size", 1) if fs.filter else 1
            fl_order = fs.filter.get("order") if fs.filter else None
            terms = {"field": fs.index_field_name, "size": fl_size}
            if fl_order:
                terms["order"] = fl_order
            aggs[fs.field_name] = {"terms": terms}
        return {"size": 0, "aggs": aggs}

    def get_filter_metadata(self, filters):
        """Return UI metadata (class_filter, label, category, ...) for each filter.

        Equivalent to SearchGatewayService.get_filter_metadata().

        Args:
            filters: dict whose keys are field names present in the response.
        Returns:
            dict mapping field_name -> settings dict.
        """
        requested = set(filters.keys())
        metadata = {}
        for fs in self.settings_filters.all():
            if fs.field_name in requested and fs.settings:
                metadata[fs.field_name] = fs.settings
        return metadata

    def get_fields_with_transforms(self):
        """Return fields that define any transform configuration.

        A field is included if it has:
        - filter transform: settings_filters[].filter.transform
        - display transform: settings_filters[].settings.display_transform
        """
        fields = {}
        for sf in self.settings_filters.all():
            flt = (sf.filter or {}).get("transform")
            disp = (sf.settings or {}).get("display_transform")
            if flt or disp:
                fields[sf.field_name] = {
                    "filter_transform": flt,
                    "display_transform": disp,
                }
        return fields

    @classmethod
    def get_by_index_name(cls, index_name):
        try:
            return cls.objects.get(index_name=index_name)
        except cls.DoesNotExist:
            return None


class SettingsFilterQuerySet(models.QuerySet):
    def for_data_source(self, data_source):
        return self.filter(data_source=data_source)

    def by_field_name(self, field_name):
        return self.filter(field_name=field_name)

    def get_by_field_name(self, field_name):
        """Return the SettingsFilter for this queryset, or None if missing.

        Tip: call this from the reverse relation:
            data_source.settings_filters.get_by_field_name(field_name="publication_year")
        """
        try:
            return self.get(field_name=field_name)
        except self.model.DoesNotExist:
            return None


class SettingsFilterManager(models.Manager.from_queryset(SettingsFilterQuerySet)):
    pass


class SettingsFilter(models.Model):
    objects = SettingsFilterManager()

    data_source = ParentalKey(
        DataSource,
        on_delete=models.CASCADE,
        related_name="settings_filters",
    )
    field_name = models.CharField(
        max_length=255,
        help_text=_("Chave do filtro, ex: 'document_type.keyword', 'publication_year'"),
    )
    index_field_name = models.CharField(
        max_length=255,
        help_text=_("Campo no índice OpenSearch, ex: 'type.keyword', 'publication_year'"),
    )
    field_autocomplete = models.CharField(
        max_length=255,
        blank=True,
        help_text=_("Campo de autocomplete no OpenSearch, se houver"),
    )
    filter = models.JSONField(
        default=dict,
        blank=True,
        help_text=_("Configuração do filtro: {size, order, transform}"),
    )
    settings = models.JSONField(
        default=dict,
        blank=True,
        help_text=_(
            "Configurações de UI: {class_filter, label, support_search_as_you_type, "
            "support_query_operator, category, display_transform, multiple_selection}"
        ),
    )

    panels = [
        FieldPanel("field_name"),
        FieldPanel("index_field_name"),
        FieldPanel("field_autocomplete"),
        FieldPanel("filter"),
        FieldPanel("settings"),
    ]

    class Meta:
        verbose_name = _("Settings Filter")
        verbose_name_plural = _("Settings Filters")
        unique_together = ("data_source", "field_name")

    def __str__(self):
        return f"{self.data_source} - {self.field_name}"

    def to_dict(self):
        result = {"index_field_name": self.index_field_name}
        if self.field_autocomplete:
            result["field_autocomplete"] = self.field_autocomplete
        if self.filter:
            result["filter"] = self.filter
        if self.settings:
            result["settings"] = self.settings
        return result
