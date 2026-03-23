from copy import deepcopy

from django.db import models
from django.utils.text import capfirst
from django.utils.translation import gettext, gettext_lazy as _
from wagtail.admin.panels import FieldPanel
from wagtail_json_widget.widgets import JSONEditorWidget

from .normalization import normalize_group_key
from .normalization import normalize_widget_name


def _deep_merge_dict(base, override):
    merged = deepcopy(base or {})
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge_dict(merged[key], value)
        else:
            merged[key] = deepcopy(value)
    return merged


def _build_default_boolean_options():
    return [
        {"value": "true", "label": gettext("Yes")},
        {"value": "false", "label": gettext("No")},
    ]


class ResolvedField:
    QUERY_OPERATOR_SUFFIX = "_operator"
    QUERY_BOOL_NOT_SUFFIX = "_bool_not"

    def __init__(self, data_source, field_name, config):
        self.data_source = data_source
        self.field_name = field_name
        self.config = deepcopy(config or {})
        self.kind = str(self.config.get("kind") or "index").strip().lower() or "index"
        self.index_field_name = str(self.config.get("index_field_name") or "").strip()

    def get_ui_settings(self):
        return dict(self.config.get("settings") or {})

    def get_ui_setting(self, key, default=None):
        return self.get_ui_settings().get(key, default)

    def get_filter_config(self):
        return dict(self.config.get("filter") or {})

    def get_filter_setting(self, key, default=None):
        return self.get_filter_config().get(key, default)

    def get_lookup_config(self):
        lookup = self.config.get("lookup")
        if not isinstance(lookup, dict):
            lookup = self.get_ui_setting("lookup")
        return dict(lookup or {})

    def get_transform_config(self):
        transform = self.get_filter_setting("transform") or {}
        return dict(transform) if isinstance(transform, dict) else {}

    def get_transform_type(self):
        return self.get_transform_config().get("type")

    def get_transform_sources(self):
        return list(self.get_transform_config().get("sources") or [])

    def get_group_key(self):
        raw_group = self.get_ui_setting("group") or self.get_ui_setting("category")
        return _normalize_group_key(raw_group, default="default")

    def get_group_meta(self):
        group_key = self.get_group_key()
        explicit_label = self.get_ui_setting("group_label")
        explicit_order = self.get_ui_setting("group_order")
        label = explicit_label or capfirst(str(group_key).replace("_", " "))
        order = explicit_order if explicit_order is not None else 999
        return {
            "key": group_key,
            "label": label,
            "order": order,
            "icon": self.get_ui_setting("group_icon"),
        }

    def get_label(self, default=None):
        label = self.get_ui_setting("label")
        if label not in (None, ""):
            return label
        return default if default is not None else self.field_name

    def get_help_text(self, default=""):
        return self.get_ui_setting("help_text", default)

    def get_placeholder(self, default=""):
        return self.get_ui_setting("placeholder", default)

    def get_default_value(self, default=None):
        default = {} if default is None else default
        configured_default = self.get_ui_setting("default_value")
        if configured_default in (None, ""):
            return default
        return configured_default

    def get_static_options(self):
        configured_options = list(self.get_ui_setting("static_options") or [])
        if configured_options:
            return configured_options

        if (
            self.get_transform_type() == "boolean"
            or self.get_ui_setting("display_transform") == "boolean"
        ):
            return _build_default_boolean_options()

        return []

    def get_dependencies(self):
        return list(self.get_ui_setting("dependencies") or [])

    def supports_query_operator(self):
        return bool(self.get_ui_setting("support_query_operator"))

    def get_operator_field_name(self):
        return f"{self.field_name}{self.QUERY_OPERATOR_SUFFIX}"

    def get_bool_not_field_name(self):
        return f"{self.field_name}{self.QUERY_BOOL_NOT_SUFFIX}"

    def get_widget_name(self):
        settings = self.get_ui_settings()
        return _normalize_widget_name(
            settings.get("widget") or settings.get("class_filter"),
            transform_type=self.get_transform_type(),
            has_lookup=bool(self.get_lookup_config()),
        )

    def allows_multiple_selection(self):
        default = self.get_widget_name() not in {"range", "text", "number", "year"}
        return self.get_ui_setting("multiple_selection", default)

    def is_preload_options(self):
        return bool(self.get_ui_setting("preload_options"))

    def is_hidden_in_form(self):
        return bool(self.get_ui_setting("hidden_in_form"))

    def get_async_endpoint(self):
        async_endpoint = self.get_ui_setting("async_endpoint")
        if async_endpoint in (None, "") and self.get_lookup_config():
            return "search_item"
        return async_endpoint or ""

    def is_searchable(self):
        return self.get_widget_name() == "lookup" or bool(self.get_async_endpoint())

    def requires_runtime_options(self):
        widget = self.get_widget_name()
        if widget in {"text", "number", "year", "range"}:
            return False
        if self.get_static_options():
            return False
        if self.kind != "index" and widget != "lookup":
            return False
        if widget == "lookup" and not self.is_preload_options():
            return False
        return True

    def get_ui_metadata(self):
        transform_config = self.get_transform_config()
        return {
            "widget": self.get_widget_name(),
            "group": self.get_group_meta(),
            "searchable": self.is_searchable(),
            "async_endpoint": self.get_async_endpoint(),
            "preload_options": self.is_preload_options(),
            "dependencies": self.get_dependencies(),
            "multiple_selection": self.allows_multiple_selection(),
            "support_query_operator": self.supports_query_operator(),
            "input_type": self.get_ui_setting("input_type", "text"),
            "min_value": self.get_ui_setting("min"),
            "max_value": self.get_ui_setting("max"),
            "step": self.get_ui_setting("step"),
            "allow_clear": self.get_ui_setting("allow_clear", True),
            "label": self.get_label(default=""),
            "help_text": self.get_help_text(default=""),
            "placeholder": self.get_placeholder(default=""),
            "default_value": self.get_default_value(default={}),
            "static_options": self.get_static_options(),
            "transform_type": transform_config.get("type"),
            "transform_sources": self.get_transform_sources(),
        }

    def get_option_limit(self, default=100):
        lookup_config = self.get_lookup_config()
        if lookup_config.get("size") not in (None, ""):
            try:
                return max(int(lookup_config.get("size")), 1)
            except (TypeError, ValueError):
                pass

        configured_size = self.get_filter_setting("size")
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
        return self.get_filter_setting("use", True) is not False

    def to_dict(self):
        result = {"kind": self.kind}
        if self.index_field_name:
            result["index_field_name"] = self.index_field_name
        if self.config.get("lookup"):
            result["lookup"] = deepcopy(self.config["lookup"])
        if self.config.get("filter"):
            result["filter"] = deepcopy(self.config["filter"])
        if self.config.get("settings"):
            result["settings"] = deepcopy(self.config["settings"])
        return result


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
            "field_settings": self.get_field_settings_schema(),
        }

    @staticmethod
    def _normalize_field_config(field_name, config):
        config = deepcopy(config or {})
        settings = dict(config.get("settings") or {})
        filter_config = dict(config.get("filter") or {})

        if config.get("transform") == "year_range":
            filter_config["transform"] = {
                "type": "year_range",
                "sources": list(config.get("source_fields") or []),
            }
        elif config.get("source_fields") and "transform" not in filter_config:
            filter_config["transform"] = {
                "type": "year_range",
                "sources": list(config.get("source_fields") or []),
            }

        lookup_config = config.get("lookup")
        if not isinstance(lookup_config, dict):
            lookup_config = settings.get("lookup")
        lookup_config = dict(lookup_config or {})

        transform_type = (filter_config.get("transform") or {}).get("type")
        widget = _normalize_widget_name(
            settings.get("widget") or settings.get("class_filter"),
            transform_type=transform_type,
            has_lookup=bool(lookup_config),
        )
        settings["widget"] = widget
        settings.pop("class_filter", None)
        settings.pop("support_search_as_you_type", None)
        settings.pop("lookup", None)

        group_key = settings.get("group") or settings.get("category")
        if group_key:
            normalized_group_key = _normalize_group_key(group_key)
            settings["group"] = normalized_group_key

        if "multiple_selection" not in settings:
            settings["multiple_selection"] = widget not in {"range", "text", "number", "year"}
        if lookup_config and "async_endpoint" not in settings:
            settings["async_endpoint"] = "search_item"

        kind = str(config.get("kind") or "index").strip().lower() or "index"
        index_field_name = str(config.get("index_field_name") or "").strip()

        normalized = {
            "kind": kind,
            "index_field_name": index_field_name,
            "filter": filter_config,
            "settings": settings,
        }
        if lookup_config:
            normalized["lookup"] = lookup_config
        return normalized

    @classmethod
    def _normalize_schema(cls, raw_field_settings):
        if not isinstance(raw_field_settings, dict):
            return {"fields": {}, "forms": {}}

        raw_fields = raw_field_settings.get("fields")
        raw_forms = raw_field_settings.get("forms")

        if isinstance(raw_fields, dict):
            fields = {
                field_name: cls._normalize_field_config(field_name, field_config)
                for field_name, field_config in raw_fields.items()
                if isinstance(field_name, str)
            }
            forms = {}
            if isinstance(raw_forms, dict):
                for form_key, form_config in raw_forms.items():
                    if not isinstance(form_key, str):
                        continue
                    normalized_form = {
                        key: deepcopy(value)
                        for key, value in (form_config or {}).items()
                        if key != "fields"
                    }
                    form_fields = []
                    for item in list((form_config or {}).get("fields") or []):
                        if isinstance(item, str):
                            form_fields.append(item)
                            continue
                        if not isinstance(item, dict):
                            continue
                        item_name = str(item.get("name") or "").strip()
                        if not item_name:
                            continue
                        form_fields.append(
                            {
                                "name": item_name,
                                "overrides": deepcopy(item.get("overrides") or {}),
                            }
                        )
                    normalized_form["fields"] = form_fields
                    forms[form_key] = normalized_form
            return {"fields": fields, "forms": forms}

        fields = {
            field_name: cls._normalize_field_config(field_name, field_config)
            for field_name, field_config in raw_field_settings.items()
            if isinstance(field_name, str)
        }
        default_form = {"fields": list(fields.keys())}
        return {"fields": fields, "forms": {"default": default_form}}

    def get_field_settings_schema(self):
        schema = self._normalize_schema(self.field_settings or {})

        # Compatibility bridge while existing DB rows are being resynced:
        # scientific indicators now expose `scope` inside the shared filter form.
        if self.index_name == "scientific_production":
            fields = schema.get("fields", {})
            forms = schema.get("forms", {})
            indicator_form = forms.get("indicator") or {}
            indicator_fields = list(indicator_form.get("fields") or [])
            has_scope_field = "scope" in fields
            has_scope_in_form = any(
                item == "scope" or (isinstance(item, dict) and str(item.get("name") or "").strip() == "scope")
                for item in indicator_fields
            )
            if has_scope_field and not has_scope_in_form:
                insert_at = 1 if indicator_fields else 0
                indicator_fields.insert(insert_at, "scope")
                forms["indicator"] = {"fields": indicator_fields}

        return schema

    @property
    def field_settings_schema(self):
        return self.get_field_settings_schema()

    @property
    def field_settings_dict(self):
        return self.get_field_settings_dict()

    def get_field_settings_dict(self, include_fields=None, exclude_fields=None):
        include_fields = set(include_fields or [])
        exclude_fields = set(exclude_fields or [])
        field_settings = {}
        for field_name, field_config in self.get_field_settings_schema().get("fields", {}).items():
            if include_fields and field_name not in include_fields:
                continue
            if field_name in exclude_fields:
                continue
            field_settings[field_name] = deepcopy(field_config)
        return field_settings

    def get_form_names(self):
        return list(self.get_field_settings_schema().get("forms", {}).keys())

    def get_form_spec(self, form_key):
        forms = self.get_field_settings_schema().get("forms", {})
        return deepcopy(forms.get(form_key) or {})

    def get_form_group_labels(self, form_key):
        group_labels = {}
        for group_key, label in (self.get_form_spec(form_key).get("group_labels") or {}).items():
            normalized_key = _normalize_group_key(group_key)
            normalized_label = str(label or "").strip()
            if normalized_key and normalized_label:
                group_labels[normalized_key] = normalized_label
        return group_labels

    def get_form_panel_groups(self, form_key):
        normalized_groups = []
        for group_key in self.get_form_spec(form_key).get("panel_groups") or []:
            normalized_key = _normalize_group_key(group_key)
            if normalized_key and normalized_key not in normalized_groups:
                normalized_groups.append(normalized_key)
        return normalized_groups

    def get_form_control_field_names(self, form_key):
        return [
            field.field_name
            for field in self.get_ordered_fields(form_key=form_key)
            if field.kind == "control"
        ]

    def get_form_index_field_names(self, form_key):
        return [
            field.field_name
            for field in self.get_ordered_fields(form_key=form_key)
            if field.kind == "index"
        ]

    def get_ordered_fields(self, form_key=None, include_fields=None, exclude_fields=None):
        include_fields = set(include_fields or [])
        exclude_fields = set(exclude_fields or [])
        schema = self.get_field_settings_schema()
        base_fields = schema.get("fields", {})
        ordered_items = []

        form_spec = self.get_form_spec(form_key) if form_key else {}
        form_fields = list(form_spec.get("fields") or [])
        if form_fields:
            for item in form_fields:
                if isinstance(item, str):
                    field_name = item
                    overrides = {}
                else:
                    field_name = str(item.get("name") or "").strip()
                    overrides = dict(item.get("overrides") or {})
                if not field_name or field_name not in base_fields:
                    continue
                merged_config = _deep_merge_dict(base_fields[field_name], overrides)
                ordered_items.append((field_name, merged_config))
        else:
            ordered_items = list(base_fields.items())

        resolved_fields = []
        for field_name, field_config in ordered_items:
            if include_fields and field_name not in include_fields:
                continue
            if field_name in exclude_fields:
                continue
            resolved_fields.append(ResolvedField(self, field_name, field_config))
        return resolved_fields

    def get_field(self, field_name, form_key=None):
        for field in self.get_ordered_fields(form_key=form_key):
            if field.field_name == field_name:
                return field
        base_config = self.get_field_settings_dict().get(field_name)
        if not base_config:
            return None
        return ResolvedField(self, field_name, base_config)

    def get_field_config(self, field_name):
        field = self.get_field(field_name)
        return field.to_dict() if field else {}

    def get_index_field_name(self, field_name):
        field = self.get_field(field_name)
        return field.index_field_name if field else field_name

    def get_field_aggregation_size(self, field_name, default=20):
        field = self.get_field(field_name)
        return field.get_option_limit(default=default) if field else default

    def get_field_label(self, field_name):
        field = self.get_field(field_name)
        return field.get_label(default=field_name) if field else field_name

    def field_allows_multiple_selection(self, field_name, form_key=None):
        field = self.get_field(field_name, form_key=form_key)
        return field.allows_multiple_selection() if field else True

    def field_supports_search_as_you_type(self, field_name):
        field = self.get_field(field_name)
        return bool(field and field.get_lookup_config())

    @property
    def build_filters_query(self):
        aggs = {}
        for field in self.get_ordered_fields():
            if not field.should_build_filter_aggregation:
                continue
            terms = {"field": field.index_field_name, "size": field.get_filter_setting("size", 1)}
            if field.get_filter_setting("order"):
                terms["order"] = field.get_filter_setting("order")
            aggs[field.field_name] = {"terms": terms}
        return {"size": 0, "aggs": aggs}

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
            field_metadata = dict(field.get_ui_settings())
            ui_metadata = field.get_ui_metadata()
            field_label = field_metadata.get("label")
            if isinstance(field_label, str) and field_label:
                field_metadata["label"] = gettext(field_label)
            group_key = ui_metadata.get("group", {}).get("key", "default")
            group_label = ui_metadata.get("group", {}).get("label")
            group_label = form_group_labels.get(group_key, group_label)
            if isinstance(group_label, str) and group_label:
                group_label = gettext(group_label)
            field_metadata["kind"] = field.kind
            field_metadata["group"] = group_key
            field_metadata["group_label"] = group_label
            field_metadata["group_order"] = ui_metadata.get("group", {}).get("order", 999)
            field_metadata["resolved_widget"] = ui_metadata.get("widget")
            field_metadata["searchable"] = bool(ui_metadata.get("searchable"))
            field_metadata["async_endpoint"] = ui_metadata.get("async_endpoint", "")
            field_metadata["preload_options"] = bool(ui_metadata.get("preload_options"))
            field_metadata["dependencies"] = list(ui_metadata.get("dependencies") or [])
            field_metadata["order"] = position
            metadata[field.field_name] = field_metadata
        return metadata

    def get_fields_with_transforms(self):
        fields = {}
        for field_name, cfg in self.get_field_settings_dict().items():
            flt = (cfg.get("filter") or {}).get("transform")
            disp = (cfg.get("settings") or {}).get("display_transform")
            if flt or disp:
                fields[field_name] = {
                    "filter_transform": flt,
                    "display_transform": disp,
                }
        return fields

    def get_query_operator_fields(self, form_key=None):
        return {
            field.field_name: field.index_field_name
            for field in self.get_ordered_fields(form_key=form_key)
            if field.supports_query_operator() and field.index_field_name
        }

    def get_index_field_name_to_filter_name_map(self, form_key=None):
        mapping = {}
        for field in self.get_ordered_fields(form_key=form_key):
            if field.index_field_name:
                mapping[field.index_field_name] = field.field_name
        return mapping

    def get_display_transform_by_field_name(self, field_name):
        field = self.get_field(field_name)
        if not field:
            return None
        return field.get_ui_setting("display_transform")

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
