from django.db import models
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _
from wagtail.admin.panels import FieldPanel
from wagtail_json_widget.widgets import JSONEditorWidget


class DataSource(models.Model):
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
    field_settings = models.JSONField(
        default=dict,
        blank=True,
        help_text=_(
            "Configuração completa dos filtros. "
            "Dict cujas chaves são field_name e valores contêm: "
            "index_field_name, field_autocomplete, filter, settings."
        ),
    )

    panels = [
        FieldPanel("index_name"),
        FieldPanel("display_name"),
        FieldPanel("source_fields"),
        FieldPanel(
            "field_settings",
            widget=JSONEditorWidget(
                options={
                    "mode": "code",
                    "modes": ["code", "tree"],
                    "search": True,
                }
            ),
        ),
    ]

    class Meta:
        verbose_name = _("Data Source")
        verbose_name_plural = _("Data Sources")

    def __str__(self):
        return self.display_name or self.index_name

    def to_dict(self):
        return {
            "index_name": self.index_name,
            "display_name": self.display_name,
            "field_settings": self.field_settings or {},
        }

    def get_field_settings_dict(self):
        return self.field_settings or {}

    @property
    def build_filters_query(self):
        """Build the ES aggregation query body for this data source's filters."""
        aggs = {}
        for field_name, cfg in (self.field_settings or {}).items():
            fl_filter = cfg.get("filter") or {}
            fl_size = fl_filter.get("size", 1)
            fl_order = fl_filter.get("order")
            terms = {"field": cfg.get("index_field_name", field_name), "size": fl_size}
            if fl_order:
                terms["order"] = fl_order
            aggs[field_name] = {"terms": terms}
        return {"size": 0, "aggs": aggs}

    def get_filter_metadata(self, filters):
        """Return UI metadata (class_filter, label, category, ...) for each filter.

        Args:
            filters: dict whose keys are field names present in the response.
        Returns:
            dict mapping field_name -> settings dict.
        """
        requested = set(filters.keys())
        metadata = {}
        for position, (field_name, cfg) in enumerate(
            (self.field_settings or {}).items()
        ):
            if field_name not in requested:
                continue
            field_metadata = dict(cfg.get("settings") or {})
            field_label = field_metadata.get("label")
            if isinstance(field_label, str) and field_label:
                field_metadata["label"] = gettext(field_label)
            field_metadata["order"] = position
            metadata[field_name] = field_metadata
        return metadata

    def get_fields_with_transforms(self):
        """Return fields that define any transform configuration.

        A field is included if it has:
        - filter transform: field_settings[key].filter.transform
        - display transform: field_settings[key].settings.display_transform
        """
        fields = {}
        for field_name, cfg in (self.field_settings or {}).items():
            flt = (cfg.get("filter") or {}).get("transform")
            disp = (cfg.get("settings") or {}).get("display_transform")
            if flt or disp:
                fields[field_name] = {
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

