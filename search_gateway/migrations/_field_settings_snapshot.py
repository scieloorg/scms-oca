from copy import deepcopy

# Frozen snapshot of the legacy canonical field-settings builder.
# Historical migrations import this module so they keep working even
# after the runtime moved to DataSource-backed schema/fixtures.


DEFAULT_YEAR_RANGE = {"start": "2019", "end": "2025"}
DEFAULT_JOURNAL_CATEGORY_ID = "Social Sciences"
DEFAULT_JOURNAL_CATEGORY_LEVEL = "field"
DEFAULT_JOURNAL_MINIMUM_PUBLICATIONS = "50"
DEFAULT_JOURNAL_PUBLICATION_YEAR = "2020"
DEFAULT_JOURNAL_RANKING_METRIC = "journal_impact_cohort_window_3y"

GROUP_LABELS = {
    "scope": "Data scope",
    "indexing": "Indexing",
    "source": "Source Identity",
    "document": "Document Core",
    "category": "Category",
    "author_affiliation": "Author Affiliation",
    "funding": "Funding",
    "institution": "Institution",
    "location": "Location",
    "ranking": "Ranking",
    "journal_identity": "Journal Identity",
    "indexing_coverage": "Indexing / Coverage",
    "graph_options": "Graph Options",
    "directory_fields": "Directory Fields",
    "other": "Other",
}

LOOKUP_CONFIGS_BY_FIELD = {
    "source_name": {
        "index_name": "lookup_source",
        "search_field": "label_search",
        "sort_field": "label",
        "value_field": "value",
        "label_field": "label",
        "source_value_field": "value",
        "source_label_field": "label",
        "size": 100,
    },
    "publisher": {
        "index_name": "lookup_publisher",
        "search_field": "label_search",
        "sort_field": "label",
        "value_field": "value",
        "label_field": "label",
        "source_value_field": "value",
        "source_label_field": "label",
        "size": 100,
    },
    "source_country": {
        "index_name": "lookup_source_country",
        "search_field": "label_search",
        "sort_field": "label",
        "value_field": "value",
        "label_field": "label",
        "source_value_field": "value",
        "source_label_field": "label",
        "size": 200,
    },
    "funder": {
        "index_name": "lookup_funder",
        "search_field": "label_search",
        "sort_field": "label",
        "value_field": "value",
        "label_field": "label",
        "source_value_field": "value",
        "source_label_field": "label",
        "size": 100,
    },
    "institution": {
        "index_name": "lookup_institution",
        "search_field": "label_search",
        "sort_field": "label",
        "value_field": "value",
        "label_field": "label",
        "source_value_field": "value",
        "source_label_field": "label",
        "size": 100,
    },
    "institutions": {
        "index_name": "lookup_institution",
        "search_field": "label_search",
        "sort_field": "label",
        "value_field": "value",
        "label_field": "label",
        "source_value_field": "value",
        "source_label_field": "label",
        "size": 100,
    },
    "subjects": {
        "index_name": "lookup_topic",
        "search_field": "label_search",
        "sort_field": "label",
        "value_field": "value",
        "label_field": "label",
        "source_value_field": "value",
        "source_label_field": "label",
        "size": 100,
    },
    "publisher_name": {
        "index_name": "lookup_publisher",
        "search_field": "label_search",
        "sort_field": "label",
        "value_field": "value",
        "label_field": "label",
        "source_value_field": "value",
        "source_label_field": "label",
        "size": 100,
    },
    "category_id": {
        "index_name": "lookup_topic",
        "search_field": "label_search",
        "sort_field": "label",
        "value_field": "value",
        "label_field": "label",
        "source_value_field": "value",
        "source_label_field": "label",
        "size": 100,
    },
    "journal_title": {
        "index_name": "lookup_source",
        "search_field": "label_search",
        "sort_field": "label",
        "source_value_field": "label",
        "source_label_field": "label",
        "size": 100,
    },
    "journal_issn": {
        "index_name": "lookup_source",
        "search_field": "label_search",
        "sort_field": "label",
        "source_value_field": "source_issn_l",
        "source_label_field": "label",
        "size": 100,
    },
}

CATEGORY_LEVEL_OPTIONS = [
    {"value": "domain", "label": "Domain"},
    {"value": "field", "label": "Field"},
    {"value": "subfield", "label": "Subfield"},
    {"value": "topic", "label": "Topic"},
]

RANKING_METRIC_OPTIONS = [
    {"value": "journal_impact_cohort", "label": "Cohort Impact (Total)", "group": "Cohort Impact"},
    {"value": "journal_impact_cohort_window_2y", "label": "Cohort Impact (2 years)", "group": "Cohort Impact"},
    {"value": "journal_impact_cohort_window_3y", "label": "Cohort Impact (3 years)", "group": "Cohort Impact"},
    {"value": "journal_impact_cohort_window_5y", "label": "Cohort Impact (5 years)", "group": "Cohort Impact"},
    {"value": "journal_citations_total", "label": "Total Citations", "group": "Citations"},
    {"value": "journal_citations_mean", "label": "Mean Citations", "group": "Citations"},
    {"value": "journal_citations_mean_window_2y", "label": "Mean Citations (2 years)", "group": "Citations"},
    {"value": "journal_citations_mean_window_3y", "label": "Mean Citations (3 years)", "group": "Citations"},
    {"value": "journal_citations_mean_window_5y", "label": "Mean Citations (5 years)", "group": "Citations"},
    {"value": "journal_publications_count", "label": "Publication Count", "group": "Publications"},
    {"value": "top_1pct_all_time_publications_share_pct", "label": "Top 1% Publications Share", "group": "Publications"},
    {"value": "top_5pct_all_time_publications_share_pct", "label": "Top 5% Publications Share", "group": "Publications"},
    {"value": "top_10pct_all_time_publications_share_pct", "label": "Top 10% Publications Share", "group": "Publications"},
    {"value": "top_50pct_all_time_publications_share_pct", "label": "Top 50% Publications Share", "group": "Publications"},
]

LIMIT_OPTIONS = [
    {"value": "10", "label": "10"},
    {"value": "25", "label": "25"},
    {"value": "50", "label": "50"},
    {"value": "100", "label": "100"},
    {"value": "200", "label": "200"},
    {"value": "500", "label": "500"},
    {"value": "1000", "label": "1000"},
]

SCIENTIFIC_BREAKDOWN_OPTIONS = [
    {"value": "scope", "label": "Scope"},
    {"value": "source_type", "label": "Source Type"},
    {"value": "document_type", "label": "Document Type"},
    {"value": "document_language", "label": "Document Language"},
    {"value": "open_access", "label": "Open Access"},
    {"value": "open_access_status", "label": "Access Type"},
    {"value": "subject_area_level_0", "label": "Domain"},
    {"value": "subject_area_level_1", "label": "Field"},
    {"value": "subject_area_level_2", "label": "Subfield"},
    {"value": "subjects", "label": "Topic"},
]

SOCIAL_BREAKDOWN_OPTIONS = [
    {"value": "directory_type", "label": "Directory Type"},
    {"value": "action", "label": "Action"},
    {"value": "classification", "label": "Classification"},
    {"value": "practice", "label": "Practice"},
    {"value": "regions", "label": "Region"},
    {"value": "states", "label": "State"},
    {"value": "cities", "label": "City"},
]


def _deep_merge(base, override):
    merged = deepcopy(base or {})
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = deepcopy(value)
    return merged


def _copy(value):
    return deepcopy(value)


def _normalize_widget_name(widget_name, *, transform_type=None, has_lookup=False):
    normalized_widget = str(widget_name or "").strip().lower()
    if normalized_widget in {"lookup", "select", "range", "text", "number", "year"}:
        return normalized_widget
    if normalized_widget in {"select2", "select"}:
        return "select"
    if normalized_widget in {"autocomplete"} or has_lookup:
        return "lookup"
    if normalized_widget in {"input", "string"}:
        return "text"
    if transform_type == "year_range":
        return "range"
    return "select"


def _normalize_legacy_field(field_name, config):
    config = _copy(config or {})
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

    class_filter = settings.pop("class_filter", None)
    settings.pop("support_search_as_you_type", None)
    settings.pop("lookup", None)
    settings.pop("category", None)
    if config.get("field_autocomplete"):
        config.pop("field_autocomplete", None)

    transform_type = (filter_config.get("transform") or {}).get("type")
    settings["widget"] = _normalize_widget_name(
        settings.get("widget") or class_filter,
        transform_type=transform_type,
        has_lookup=bool(lookup_config),
    )
    if "multiple_selection" not in settings:
        settings["multiple_selection"] = settings["widget"] not in {"range", "text", "number", "year"}

    normalized = {
        "kind": str(config.get("kind") or "index").strip().lower() or "index",
        "index_field_name": str(config.get("index_field_name") or "").strip(),
        "filter": filter_config,
        "settings": settings,
    }
    if lookup_config:
        normalized["lookup"] = lookup_config
    return normalized


def _normalize_fields(legacy_fields):
    normalized = {}
    for field_name, field_config in (legacy_fields or {}).items():
        if not isinstance(field_name, str):
            continue
        normalized[field_name] = _normalize_legacy_field(field_name, field_config)
    return normalized


def _patch_field(fields, field_name, patch):
    fields[field_name] = _deep_merge(fields.get(field_name) or {}, patch)


def _ensure_field(fields, field_name, field_config):
    if field_name not in fields:
        fields[field_name] = _copy(field_config)
    else:
        fields[field_name] = _deep_merge(field_config, fields[field_name])


def _form_field(name, overrides=None):
    if overrides:
        return {"name": name, "overrides": _copy(overrides)}
    return name


def _group_settings(group, order):
    return {
        "group": group,
        "group_order": order,
    }


def _form_group_labels(*group_keys):
    return {
        str(group_key): GROUP_LABELS[str(group_key)]
        for group_key in group_keys
        if str(group_key) in GROUP_LABELS
    }


def _build_scientific_fields(legacy_fields):
    fields = _normalize_fields(legacy_fields)

    _ensure_field(
        fields,
        "document_publication_year_range",
        {
            "kind": "index",
            "index_field_name": "publication_year",
            "filter": {
                "use": False,
                "transform": {
                    "type": "year_range",
                    "sources": [
                        "document_publication_year_start",
                        "document_publication_year_end",
                    ],
                },
            },
            "settings": {
                "widget": "range",
                "label": "Publication Year",
                "default_value": _copy(DEFAULT_YEAR_RANGE),
                **_group_settings("document", 30),
            },
        },
    )

    base_patches = {
        "scope": {
            "settings": {
                "label": "Scope",
                "widget": "select",
                **_group_settings("scope", 0),
            }
        },
        "source_indexed_in": {
            "settings": {
                "label": "Indexed In",
                "widget": "select",
                **_group_settings("indexing", 10),
            }
        },
        "source_type": {
            "settings": {
                "label": "Source Type",
                "widget": "select",
                **_group_settings("indexing", 10),
            }
        },
        "source_name": {
            "index_field_name": "sources.id",
            "lookup": _copy(LOOKUP_CONFIGS_BY_FIELD["source_name"]),
            "filter": {"use": False},
            "settings": {
                "label": "Source",
                "widget": "lookup",
                "support_query_operator": True,
                **_group_settings("source", 20),
            },
        },
        "publisher": {
            "index_field_name": "publishers.id",
            "lookup": _copy(LOOKUP_CONFIGS_BY_FIELD["publisher"]),
            "filter": {"use": False},
            "settings": {
                "label": "Publisher",
                "widget": "lookup",
                "support_query_operator": True,
                **_group_settings("source", 20),
            },
        },
        "source_country": {
            "lookup": _copy(LOOKUP_CONFIGS_BY_FIELD["source_country"]),
            "filter": {"use": False},
            "settings": {
                "label": "Source Country",
                "widget": "lookup",
                "display_transform": "country",
                "support_query_operator": True,
                **_group_settings("source", 20),
            },
        },
        "publication_year": {
            "settings": {
                "label": "Publication Year",
                "widget": "select",
                **_group_settings("document", 30),
            }
        },
        "document_publication_year_range": {
            "settings": {
                "label": "Publication Year",
                "widget": "range",
                **_group_settings("document", 30),
            }
        },
        "document_type": {
            "settings": {
                "label": "Document Type",
                "widget": "select",
                **_group_settings("document", 30),
            }
        },
        "document_language": {
            "settings": {
                "label": "Document Language",
                "widget": "select",
                "display_transform": "language",
                "support_query_operator": True,
                **_group_settings("document", 30),
            }
        },
        "open_access": {
            "settings": {
                "label": "Open Access",
                "widget": "select",
                "multiple_selection": False,
                "display_transform": "boolean",
                **_group_settings("document", 30),
            }
        },
        "open_access_status": {
            "settings": {
                "label": "Access Type",
                "widget": "select",
                **_group_settings("document", 30),
            }
        },
        "subject_area_level_0": {
            "settings": {
                "label": "Domain",
                "widget": "select",
                **_group_settings("category", 40),
            }
        },
        "subject_area_level_1": {
            "settings": {
                "label": "Field",
                "widget": "select",
                **_group_settings("category", 40),
            }
        },
        "subject_area_level_2": {
            "settings": {
                "label": "Subfield",
                "widget": "select",
                **_group_settings("category", 40),
            }
        },
        "subjects": {
            "lookup": _copy(LOOKUP_CONFIGS_BY_FIELD["subjects"]),
            "filter": {"use": False},
            "settings": {
                "label": "Topic",
                "widget": "lookup",
                **_group_settings("category", 40),
            },
        },
        "institution": {
            "index_field_name": "authorships.institutions.id",
            "lookup": _copy(LOOKUP_CONFIGS_BY_FIELD["institution"]),
            "filter": {"use": False},
            "settings": {
                "label": "Institution",
                "widget": "lookup",
                **_group_settings("author_affiliation", 60),
            },
        },
        "funder": {
            "index_field_name": "funders.id",
            "lookup": _copy(LOOKUP_CONFIGS_BY_FIELD["funder"]),
            "filter": {"use": False},
            "settings": {
                "label": "Funder",
                "widget": "lookup",
                "support_query_operator": True,
                **_group_settings("funding", 50),
            },
        },
        "country": {
            "settings": {
                "label": "Country",
                "widget": "select",
                "display_transform": "country",
                "support_query_operator": True,
                **_group_settings("author_affiliation", 60),
            }
        },
        "cited_by_count": {
            "settings": {
                "label": "Cited by Count",
                "widget": "select",
                **_group_settings("other", 90),
            }
        },
        "breakdown_variable": {
            "kind": "control",
            "settings": {
                "label": "Breakdown Variable",
                "widget": "select",
                "multiple_selection": False,
                "allow_clear": True,
                "static_options": _copy(SCIENTIFIC_BREAKDOWN_OPTIONS),
                **_group_settings("graph_options", 0),
            },
        },
    }

    for field_name, patch in base_patches.items():
        _patch_field(fields, field_name, patch)

    search_form = {
        "group_labels": _form_group_labels(
            "scope",
            "indexing",
            "source",
            "document",
            "category",
            "funding",
            "institution",
            "author_affiliation",
        ),
        "fields": [
            "scope",
            "source_indexed_in",
            "source_type",
            _form_field("source_name", {"settings": {"support_query_operator": False}}),
            _form_field("publisher", {"settings": {"support_query_operator": False}}),
            _form_field("source_country", {"settings": {"support_query_operator": False}}),
            "publication_year",
            "document_type",
            _form_field("document_language", {"settings": {"support_query_operator": False}}),
            "open_access",
            "open_access_status",
            "subject_area_level_0",
            "subject_area_level_1",
            "subject_area_level_2",
            "subjects",
            _form_field("funder", {"settings": {"support_query_operator": False}}),
            "institution",
            _form_field("country", {"settings": {"support_query_operator": False}}),
        ]
    }
    indicator_form = {
        "group_labels": _form_group_labels(
            "graph_options",
            "scope",
            "indexing",
            "source",
            "document",
            "category",
            "funding",
            "institution",
            "author_affiliation",
        ),
        "fields": [
            "breakdown_variable",
            "scope",
            "source_indexed_in",
            "source_type",
            _form_field("source_name", {"settings": {"multiple_selection": False}}),
            _form_field("publisher", {"settings": {"multiple_selection": False}}),
            _form_field("source_country", {"settings": {"multiple_selection": False}}),
            "publication_year",
            "document_type",
            _form_field("document_language", {"settings": {"multiple_selection": False}}),
            "open_access",
            "open_access_status",
            "subject_area_level_0",
            "subject_area_level_1",
            "subject_area_level_2",
            _form_field("funder", {"settings": {"multiple_selection": False}}),
            "institution",
            "country",
        ]
    }

    return {"fields": fields, "forms": {"search": search_form, "indicator": indicator_form}}


def _build_social_fields(legacy_fields):
    fields = _normalize_fields(legacy_fields)

    _ensure_field(
        fields,
        "document_publication_year_range",
        {
            "kind": "index",
            "index_field_name": "creation_year",
            "filter": {
                "use": False,
                "transform": {
                    "type": "year_range",
                    "sources": [
                        "document_publication_year_start",
                        "document_publication_year_end",
                    ],
                },
            },
            "settings": {
                "widget": "range",
                "label": "Creation Year",
                "default_value": _copy(DEFAULT_YEAR_RANGE),
                **_group_settings("document", 10),
            },
        },
    )

    base_patches = {
        "document_publication_year_range": {
            "settings": {
                "label": "Creation Year",
                "widget": "range",
                **_group_settings("document", 10),
            }
        },
        "publication_year": {
            "settings": {
                "label": "Creation Year",
                "widget": "select",
                **_group_settings("document", 10),
            }
        },
        "action": {
            "settings": {
                "label": "Action",
                "widget": "select",
                **_group_settings("directory_fields", 20),
            }
        },
        "thematic_level_0": {
            "settings": {
                "label": "Division",
                "widget": "select",
                **_group_settings("directory_fields", 20),
            }
        },
        "thematic_level_1": {
            "settings": {
                "label": "Area",
                "widget": "select",
                **_group_settings("directory_fields", 20),
            }
        },
        "thematic_level_2": {
            "settings": {
                "label": "Subarea",
                "widget": "select",
                **_group_settings("directory_fields", 20),
            }
        },
        "practice": {
            "settings": {
                "label": "Practice",
                "widget": "select",
                **_group_settings("directory_fields", 20),
            }
        },
        "institutions": {
            "lookup": _copy(LOOKUP_CONFIGS_BY_FIELD["institutions"]),
            "filter": {"use": False},
            "settings": {
                "label": "Institution",
                "widget": "lookup",
                **_group_settings("institution", 30),
            },
        },
        "classification": {
            "settings": {
                "label": "Classification",
                "widget": "select",
                **_group_settings("directory_fields", 20),
            }
        },
        "cities": {
            "settings": {
                "label": "City",
                "widget": "select",
                **_group_settings("location", 40),
            }
        },
        "states": {
            "settings": {
                "label": "State",
                "widget": "select",
                **_group_settings("location", 40),
            }
        },
        "regions": {
            "settings": {
                "label": "Region",
                "widget": "select",
                **_group_settings("location", 40),
            }
        },
        "directory_type": {
            "settings": {
                "label": "Directory Type",
                "widget": "select",
                **_group_settings("directory_fields", 20),
            }
        },
        "start_date_year": {
            "settings": {
                "label": "Registration Year",
                "widget": "select",
                **_group_settings("directory_fields", 20),
            }
        },
        "breakdown_variable": {
            "kind": "control",
            "settings": {
                "label": "Breakdown Variable",
                "widget": "select",
                "multiple_selection": False,
                "allow_clear": True,
                "static_options": _copy(SOCIAL_BREAKDOWN_OPTIONS),
                **_group_settings("graph_options", 0),
            },
        },
    }

    for field_name, patch in base_patches.items():
        _patch_field(fields, field_name, patch)

    search_form = {
        "group_labels": _form_group_labels(
            "document",
            "directory_fields",
            "institution",
            "location",
        ),
        "fields": [
            "publication_year",
            "directory_type",
            "action",
            "thematic_level_0",
            "thematic_level_1",
            "thematic_level_2",
            "classification",
            "practice",
            "institutions",
            "regions",
            "states",
            "cities",
            "start_date_year",
        ]
    }
    indicator_form = {
        "group_labels": _form_group_labels(
            "graph_options",
            "document",
            "directory_fields",
            "institution",
            "location",
        ),
        "fields": [
            "breakdown_variable",
            "publication_year",
            "directory_type",
            "action",
            "thematic_level_0",
            "thematic_level_1",
            "thematic_level_2",
            "classification",
            "practice",
            "institutions",
            "regions",
            "states",
            "cities",
            "start_date_year",
        ]
    }

    return {"fields": fields, "forms": {"search": search_form, "indicator": indicator_form}}


def _build_journal_metrics_fields(legacy_fields):
    fields = _normalize_fields(legacy_fields)

    base_patches = {
        "country": {
            "settings": {
                "label": "Country",
                "widget": "select",
                "multiple_selection": False,
                **_group_settings("journal_identity", 20),
            }
        },
        "journal_title": {
            "lookup": _copy(LOOKUP_CONFIGS_BY_FIELD["journal_title"]),
            "filter": {"use": False},
            "settings": {
                "label": "Journal",
                "widget": "lookup",
                "multiple_selection": False,
                **_group_settings("journal_identity", 20),
            },
        },
        "journal_issn": {
            "lookup": _copy(LOOKUP_CONFIGS_BY_FIELD["journal_issn"]),
            "filter": {"use": False},
            "settings": {
                "label": "ISSN",
                "widget": "lookup",
                "multiple_selection": False,
                **_group_settings("journal_identity", 20),
            },
        },
        "journal_id": {
            "settings": {
                "label": "Journal ID",
                "widget": "select",
                "hidden_in_form": True,
                **_group_settings("journal_identity", 20),
            }
        },
        "publisher_name": {
            "lookup": _copy(LOOKUP_CONFIGS_BY_FIELD["publisher_name"]),
            "filter": {"use": False},
            "settings": {
                "label": "Publisher",
                "widget": "lookup",
                "multiple_selection": False,
                **_group_settings("journal_identity", 20),
            },
        },
        "collection": {
            "settings": {
                "label": "SciELO Collection",
                "widget": "select",
                "multiple_selection": False,
                **_group_settings("journal_identity", 20),
            }
        },
        "category_level": {
            "settings": {
                "label": "Category Type",
                "widget": "select",
                "multiple_selection": False,
                "static_options": _copy(CATEGORY_LEVEL_OPTIONS),
                "default_value": DEFAULT_JOURNAL_CATEGORY_LEVEL,
                "display_transform": "category_level",
                **_group_settings("ranking", 0),
            }
        },
        "category_id": {
            "lookup": _copy(LOOKUP_CONFIGS_BY_FIELD["category_id"]),
            "filter": {"use": False},
            "settings": {
                "label": "Category",
                "widget": "lookup",
                "multiple_selection": False,
                "preload_options": True,
                "dependencies": ["category_level"],
                "lookup_use_data_source_values": True,
                "default_value": DEFAULT_JOURNAL_CATEGORY_ID,
                **_group_settings("ranking", 0),
            },
        },
        "publication_year": {
            "settings": {
                "label": "Publication Year",
                "widget": "year",
                "multiple_selection": False,
                "input_type": "text",
                "default_value": DEFAULT_JOURNAL_PUBLICATION_YEAR,
                **_group_settings("ranking", 0),
            }
        },
        "is_scielo": {
            "settings": {
                "label": "Is SciELO",
                "widget": "select",
                "multiple_selection": False,
                "display_transform": "boolean",
                **_group_settings("indexing_coverage", 30),
            }
        },
        "is_scopus": {
            "settings": {
                "label": "Is Scopus",
                "widget": "select",
                "multiple_selection": False,
                "display_transform": "boolean",
                **_group_settings("indexing_coverage", 30),
            }
        },
        "is_wos": {
            "settings": {
                "label": "Is WoS",
                "widget": "select",
                "multiple_selection": False,
                "display_transform": "boolean",
                **_group_settings("indexing_coverage", 30),
            }
        },
        "is_doaj": {
            "settings": {
                "label": "Is DOAJ",
                "widget": "select",
                "multiple_selection": False,
                "display_transform": "boolean",
                **_group_settings("indexing_coverage", 30),
            }
        },
        "is_journal_oa": {
            "settings": {
                "label": "Is Open Access",
                "widget": "select",
                "multiple_selection": False,
                "display_transform": "boolean",
                **_group_settings("journal_identity", 20),
            }
        },
        "is_openalex": {
            "settings": {
                "label": "Is OpenAlex",
                "widget": "select",
                "multiple_selection": False,
                "display_transform": "boolean",
                **_group_settings("indexing_coverage", 30),
            }
        },
        "is_journal_multilingual": {
            "settings": {
                "label": "Is Multilingual",
                "widget": "select",
                "multiple_selection": False,
                "display_transform": "boolean",
                **_group_settings("journal_identity", 20),
            }
        },
        "ranking_metric": {
            "kind": "control",
            "settings": {
                "label": "Ranking metric",
                "widget": "select",
                "multiple_selection": False,
                "static_options": _copy(RANKING_METRIC_OPTIONS),
                "default_value": DEFAULT_JOURNAL_RANKING_METRIC,
                "help_text": (
                    "Cohort Impact ranks journals by citations received by documents "
                    "published in the selected year and category."
                ),
                **_group_settings("ranking", 0),
            },
        },
        "minimum_publications": {
            "kind": "control",
            "settings": {
                "label": "Minimum publications",
                "widget": "number",
                "multiple_selection": False,
                "input_type": "number",
                "min": 1,
                "step": 1,
                "default_value": DEFAULT_JOURNAL_MINIMUM_PUBLICATIONS,
                "help_text": (
                    "Minimum number of publications required for the journal in "
                    "the selected category and year."
                ),
                **_group_settings("ranking", 0),
            },
        },
        "limit": {
            "kind": "control",
            "settings": {
                "label": "Number of results",
                "widget": "select",
                "multiple_selection": False,
                "static_options": _copy(LIMIT_OPTIONS),
                "default_value": "100",
                **_group_settings("ranking", 0),
            },
        },
    }

    for field_name, patch in base_patches.items():
        _patch_field(fields, field_name, patch)

    journal_metrics_form = {
        "group_labels": _form_group_labels(
            "ranking",
            "journal_identity",
            "indexing_coverage",
        ),
        "panel_groups": ["ranking"],
        "fields": [
            "publication_year",
            "category_level",
            "category_id",
            "ranking_metric",
            "minimum_publications",
            "limit",
            "country",
            "publisher_name",
            "collection",
            "journal_title",
            "journal_issn",
            "is_journal_oa",
            "is_journal_multilingual",
            "is_scielo",
            "is_scopus",
            "is_wos",
            "is_doaj",
            "is_openalex",
        ]
    }

    return {"fields": fields, "forms": {"journal_metrics": journal_metrics_form}}


def wrap_legacy_field_settings(field_settings):
    normalized_fields = _normalize_fields(field_settings)
    return {
        "fields": normalized_fields,
        "forms": {
            "default": {
                "fields": list(normalized_fields.keys()),
            }
        },
    }


def build_canonical_field_settings(index_name, raw_field_settings):
    if isinstance(raw_field_settings, dict) and isinstance(raw_field_settings.get("fields"), dict):
        legacy_fields = raw_field_settings.get("fields") or {}
    else:
        legacy_fields = raw_field_settings or {}

    normalized_index_name = str(index_name or "").strip()
    if normalized_index_name == "scientific_production":
        return _build_scientific_fields(legacy_fields)
    if normalized_index_name == "social_production":
        return _build_social_fields(legacy_fields)
    if normalized_index_name == "journal_metrics_by_*":
        return _build_journal_metrics_fields(legacy_fields)
    return wrap_legacy_field_settings(legacy_fields)


def unwrap_field_settings(field_settings):
    if isinstance(field_settings, dict) and isinstance(field_settings.get("fields"), dict):
        return _copy(field_settings.get("fields") or {})
    return _copy(field_settings or {})
