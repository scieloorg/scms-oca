from django.db import models
from django.utils.text import capfirst
from django.utils.translation import gettext, gettext_lazy as _
from wagtail.admin.panels import FieldPanel
from wagtail_json_widget.widgets import JSONEditorWidget


def _merge_field_section(base_section, override_section, *, nested_keys=()):
    if not isinstance(base_section, dict) or not isinstance(override_section, dict):
        return override_section

    merged = {**base_section, **override_section}
    for nested_key in nested_keys:
        base_nested = base_section.get(nested_key)
        override_nested = override_section.get(nested_key)
        if isinstance(base_nested, dict) and isinstance(override_nested, dict):
            merged[nested_key] = {**base_nested, **override_nested}
    return merged


def _merge_field_config(base_config, override_config):
    merged = dict(base_config or {})
    for key, value in (override_config or {}).items():
        if key == "filter":
            merged[key] = _merge_field_section(merged.get(key), value, nested_keys=("transform",))
            continue
        if key in {"lookup", "settings"}:
            merged[key] = _merge_field_section(merged.get(key), value)
            continue
        merged[key] = value
    return merged


def _build_default_boolean_options():
    return [
        {"value": "true", "label": gettext("Yes")},
        {"value": "false", "label": gettext("No")},
    ]


class ResolvedField:
    QUERY_OPERATOR_SUFFIX = "_operator"
    QUERY_BOOL_NOT_SUFFIX = "_bool_not"

    def __init__(self, field_name, config):
        self.field_name = field_name
        self.config = config or {}
        self.ui_settings = self.config.get("settings") or {}
        self.filter_config = self.config.get("filter") or {}
        self.lookup_config = self.config.get("lookup") or {}
        self.transform_config = self.filter_config.get("transform") or {}
        self.kind = str(self.config.get("kind") or "index").strip().lower() or "index"
        self.index_field_name = str(self.config.get("index_field_name") or "").strip()

    @property
    def lookup(self):
        return self.lookup_config

    @property
    def transform_sources(self):
        return self.transform_config.get("sources") or []

    @property
    def group_meta(self):
        group_key = self.ui_settings.get("group") or "default"
        explicit_label = self.ui_settings.get("group_label")
        explicit_order = self.ui_settings.get("group_order")
        label = explicit_label or capfirst(str(group_key).replace("_", " "))
        order = explicit_order if explicit_order is not None else 999
        return {
            "key": group_key,
            "label": label,
            "order": order,
            "icon": self.ui_settings.get("group_icon"),
        }

    @property
    def label(self):
        label = self.ui_settings.get("label")
        if label not in (None, ""):
            return label
        return self.field_name

    @property
    def default_value(self):
        configured_default = self.ui_settings.get("default_value")
        if configured_default in (None, ""):
            return {}
        return configured_default

    @property
    def static_options(self):
        configured_options = self.ui_settings.get("static_options") or []
        if configured_options:
            return configured_options

        if (
            self.transform_config.get("type") == "boolean"
            or self.display_transform == "boolean"
        ):
            return _build_default_boolean_options()

        return []

    @property
    def supports_query_operator(self):
        return bool(self.ui_settings.get("support_query_operator"))

    @property
    def operator_field_name(self):
        return f"{self.field_name}{self.QUERY_OPERATOR_SUFFIX}"

    @property
    def bool_not_field_name(self):
        return f"{self.field_name}{self.QUERY_BOOL_NOT_SUFFIX}"

    @property
    def widget_name(self):
        return self.ui_settings.get("widget") or ("lookup" if self.lookup else "")

    @property
    def allows_multiple_selection(self):
        default = self.widget_name not in {"range", "text", "number", "year"}
        return self.ui_settings.get("multiple_selection", default)

    @property
    def preload_options(self):
        return bool(self.ui_settings.get("preload_options"))

    @property
    def hidden_in_form(self):
        return bool(self.ui_settings.get("hidden_in_form"))

    @property
    def async_endpoint(self):
        async_endpoint = self.ui_settings.get("async_endpoint")
        if async_endpoint in (None, "") and self.lookup:
            return "search_item"
        return async_endpoint or ""

    @property
    def searchable(self):
        return self.widget_name == "lookup" or bool(self.async_endpoint)

    @property
    def help_text(self):
        return self.ui_settings.get("help_text", "")

    @property
    def placeholder(self):
        return self.ui_settings.get("placeholder", "")

    @property
    def dependencies(self):
        return self.ui_settings.get("dependencies") or []

    @property
    def input_type(self):
        return self.ui_settings.get("input_type", "text")

    @property
    def min_value(self):
        return self.ui_settings.get("min")

    @property
    def max_value(self):
        return self.ui_settings.get("max")

    @property
    def step(self):
        return self.ui_settings.get("step")

    @property
    def allow_clear(self):
        return self.ui_settings.get("allow_clear", True)

    @property
    def display_transform(self):
        return self.ui_settings.get("display_transform")

    @property
    def lookup_uses_data_source_values(self):
        return bool(self.ui_settings.get("lookup_use_data_source_values"))

    @property
    def filter_size(self):
        return self.filter_config.get("size")

    @property
    def filter_order(self):
        return self.filter_config.get("order")

    @property
    def requires_runtime_options(self):
        widget = self.widget_name
        if widget in {"text", "number", "year", "range"}:
            return False
        if self.static_options:
            return False
        if self.kind != "index" and widget != "lookup":
            return False
        if widget == "lookup" and not self.preload_options:
            return False
        return True

    def build_filter_metadata(self, *, order=0, group_label_override=None):
        field_metadata = dict(self.ui_settings)

        field_label = field_metadata.get("label")
        if isinstance(field_label, str) and field_label:
            field_metadata["label"] = gettext(field_label)

        group_meta = self.group_meta
        group_key = group_meta.get("key", "default")
        group_label = group_label_override or group_meta.get("label")
        if isinstance(group_label, str) and group_label:
            group_label = gettext(group_label)

        field_metadata.update(
            {
                "kind": self.kind,
                "group": group_key,
                "group_label": group_label,
                "group_order": group_meta.get("order", 999),
                "resolved_widget": self.widget_name,
                "searchable": self.searchable,
                "async_endpoint": self.async_endpoint,
                "preload_options": self.preload_options,
                "dependencies": list(self.dependencies),
                "order": order,
            }
        )
        return field_metadata

    def get_option_limit(self, default=100):
        lookup_config = self.lookup
        if lookup_config.get("size") not in (None, ""):
            try:
                return max(int(lookup_config.get("size")), 1)
            except (TypeError, ValueError):
                pass

        configured_size = self.filter_size
        if configured_size not in (None, ""):
            try:
                configured_size = int(configured_size)
            except (TypeError, ValueError):
                configured_size = None
        if configured_size:
            return max(configured_size, 1 if self.should_build_filter_aggregation else default)
        return default

    @property
    def should_build_filter_aggregation(self):
        if self.kind != "index" or not self.index_field_name:
            return False
        return self.filter_config.get("use", True) is not False


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
            "Configuração completa dos filtros e formulários. "
            "Shape canônico: {fields: {...}, forms: {...}}."
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
            "source_fields": self.source_fields or [],
            "field_settings": self.field_settings_schema,
        }

    @property
    def field_settings_schema(self):
        return self.field_settings or {"fields": {}, "forms": {}}

    @property
    def fields_schema(self):
        return self.field_settings_schema.get("fields") or {}

    @property
    def forms_schema(self):
        return self.field_settings_schema.get("forms") or {}

    @property
    def field_settings_dict(self):
        return self.fields_schema

    @staticmethod
    def _normalize_form_field_item(item):
        if isinstance(item, str):
            return item, {}
        return str(item.get("name") or "").strip(), item.get("overrides") or {}

    def _form_spec(self, form_key):
        return self.forms_schema.get(form_key) or {}

    def _get_ordered_field_items(self, form_key=None):
        base_fields = self.fields_schema
        if not form_key:
            return list(base_fields.items())

        form_fields = list(self._form_spec(form_key).get("fields") or [])
        if not form_fields:
            return list(base_fields.items())

        ordered_items = []
        for item in form_fields:
            field_name, overrides = self._normalize_form_field_item(item)
            if not field_name or field_name not in base_fields:
                continue
            ordered_items.append((field_name, _merge_field_config(base_fields[field_name], overrides)))
        return ordered_items

    def get_field_settings_dict(self, include_fields=None, exclude_fields=None):
        include_fields = set(include_fields or [])
        exclude_fields = set(exclude_fields or [])
        if not include_fields and not exclude_fields:
            return self.fields_schema

        field_settings = {}
        for field_name, field_config in self.fields_schema.items():
            if include_fields and field_name not in include_fields:
                continue
            if field_name in exclude_fields:
                continue
            field_settings[field_name] = field_config
        return field_settings

    def get_form_group_labels(self, form_key):
        return {
            group_key: normalized_label
            for group_key, label in (self._form_spec(form_key).get("group_labels") or {}).items()
            if group_key and (normalized_label := str(label or "").strip())
        }

    def get_form_panel_groups(self, form_key):
        normalized_groups = []
        for group_key in self._form_spec(form_key).get("panel_groups") or []:
            if group_key and group_key not in normalized_groups:
                normalized_groups.append(group_key)
        return normalized_groups

    def get_form_control_field_names(self, form_key):
        return self._get_form_field_names_by_kind(form_key, "control")

    def _get_form_field_names_by_kind(self, form_key, kind):
        return [
            field.field_name
            for field in self.get_ordered_fields(form_key=form_key)
            if field.kind == kind
        ]

    def get_ordered_fields(self, form_key=None, include_fields=None, exclude_fields=None):
        include_fields = set(include_fields or [])
        exclude_fields = set(exclude_fields or [])
        resolved_fields = []
        for field_name, field_config in self._get_ordered_field_items(form_key=form_key):
            if include_fields and field_name not in include_fields:
                continue
            if field_name in exclude_fields:
                continue
            resolved_fields.append(ResolvedField(field_name, field_config))
        return resolved_fields

    def get_field(self, field_name, form_key=None):
        for candidate_name, field_config in self._get_ordered_field_items(form_key=form_key):
            if candidate_name == field_name:
                return ResolvedField(field_name, field_config)

        base_config = self.fields_schema.get(field_name)
        if not base_config:
            return None
        return ResolvedField(field_name, base_config)

    def get_index_field_name(self, field_name):
        field = self.get_field(field_name)
        if not field or not field.index_field_name:
            return field_name
        return field.index_field_name

    def get_filter_metadata(self, filters, form_key=None, include_fields=None, exclude_fields=None):
        requested = set((filters or {}).keys())
        form_group_labels = self.get_form_group_labels(form_key) if form_key else {}
        metadata = {}
        for position, field in enumerate(
            self.get_ordered_fields(
                form_key=form_key,
                include_fields=include_fields,
                exclude_fields=exclude_fields,
            )
        ):
            if requested and field.field_name not in requested:
                continue
            group_key = field.group_meta.get("key", "default")
            metadata[field.field_name] = field.build_filter_metadata(
                order=position,
                group_label_override=form_group_labels.get(group_key),
            )
        return metadata

    def get_fields_with_transforms(self):
        return {
            field_name: {
                "filter_transform": (cfg.get("filter") or {}).get("transform"),
                "display_transform": (cfg.get("settings") or {}).get("display_transform"),
            }
            for field_name, cfg in self.fields_schema.items()
            if (cfg.get("filter") or {}).get("transform")
            or (cfg.get("settings") or {}).get("display_transform")
        }

    def get_index_field_name_to_filter_name_map(self, form_key=None):
        return {
            field.index_field_name: field.field_name
            for field in self.get_ordered_fields(form_key=form_key)
            if field.index_field_name
        }

    @classmethod
    def get_by_index_name(cls, index_name):
        try:
            return cls.objects.get(index_name=index_name)
        except cls.DoesNotExist:
            return None

    @classmethod
    def resolve(cls, identifier):
        if not identifier:
            return None
        return cls.get_by_index_name(str(identifier).strip())
