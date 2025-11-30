from django.conf import settings
from django.utils.translation import gettext_lazy as _


# Mapping from data source name to index and field settings
DATA_SOURCES = {
  "world": {
    "index_name": settings.ES_INDEX_SCI_PROD_WORLD,
    "display_name": _("Scientific Production - World"),
    "field_settings": {
      "source_index_open_alex": {
        "index_field_name": "indexed_in",
        "filter": {
          "aggregation_type": "keyword",
          "size": 100,
          "order": {
            "_key": "asc"
          },
        }
      },
      "source_index_scielo": {
        "index_field_name": "primary_location.source.scl.indexed_in",
        "filter": {
          "aggregation_type": "keyword",
          "size": 100,
          "order": {
            "_key": "asc"
          },
        }
      },
      "source_type": {
        "index_field_name": "primary_location.source.type",
        "filter": {
          "aggregation_type": "keyword",
          "size": 100,
          "order": {
            "_key": "asc"
          },
        }
      },
      "access_type": {
        "index_field_name": "open_access.oa_status",
        "filter": {
          "aggregation_type": "keyword",
          "size": 20,
          "order": {
            "_key": "asc"
          },
        }
      },
      "document_language": {
        "index_field_name": "language",
        "filter": {
          "aggregation_type": "keyword",
          "size": 200,
          "order": {
            "_key": "asc"
          },
        }
      },
      "document_type": {
        "index_field_name": "type",
        "filter": {
          "aggregation_type": "keyword",
          "size": 100,
          "order": {
            "_key": "asc"
          },
        }
      },
      "open_access": {
        "index_field_name": "open_access.is_oa",
        "filter": {
          "aggregation_type": "ignore",
          "transform": {
            "type": "boolean"
          },
          "size": 2,
          "order": {
            "_key": "asc"
          },
        }
      },
      "publication_year": {
        "index_field_name": "publication_year",
        "filter": {
          "aggregation_type": "ignore",
          "size": 100,
          "order": {
            "_key": "desc"
          },
        }
      },
      "subject_area_level_0": {
        "index_field_name": "thematic_areas.level0",
        "filter": {
          "aggregation_type": "keyword",
          "size": 10,
          "order": {
            "_key": "asc"
          },
        }
      },
      "subject_area_level_1": {
        "index_field_name": "thematic_areas.level1",
        "filter": {
          "aggregation_type": "keyword",
          "size": 20,
          "order": {
            "_key": "asc"
          },
        }
      },
      "subject_area_level_2": {
        "index_field_name": "thematic_areas.level2",
        "filter": {
          "aggregation_type": "keyword",
          "size": 50,
          "order": {
            "_key": "asc"
          },
        }
      },
      "institution": {
        "index_field_name": "authorships.institutions.display_name",
        "filter": {
          "aggregation_type": "keyword",
          "size": 1,
          "order": {
            "_key": "asc"
          },
        }
      },
      "country": {
        "index_field_name": "authorships.countries",
        "filter": {
          "aggregation_type": "keyword",
          "size": 400,
          "order": {
            "_key": "asc"
          },
          "support_query_operator": True
        }
      },
      "region_world": {
        "index_field_name": "geos.scimago_regions",
        "filter": {
          "aggregation_type": "keyword",
          "size": 20,
          "order": {
            "_key": "asc"
          },
        }
      },
      "cited_by_count": {
        "index_field_name": "cited_by_count",
        "filter": {
          "size": 10,
          "order": {
            "_key": "desc"
          },
        }
      },
      "source_country": {
        "index_field_name": "journal_metadata.country",
        "filter": {
          "aggregation_type": "keyword",
          "size": 300,
          "order": {
            "_key": "asc"
          },
        }
      },
      "source_name": {
        "index_field_name": "primary_location.source.display_name",
        "filter": {
          "aggregation_type": "keyword",
          "size": 1,
          "order": {
            "_key": "asc"
          },
        }
      },
      "issn": {
        "index_field_name": "primary_location.source.issn",
        "filter": {
          "aggregation_type": "keyword",
          "size": 1,
          "order": {
            "_key": "asc"
          },
        }
      }
    }
  },
  "brazil": {
    "index_name": settings.ES_INDEX_SCI_PROD_BRAZIL,
    "display_name": _("Scientific Production - Brazil"),
    "field_settings": {
      "source_index_open_alex": {
        "index_field_name": "indexed_in",
        "filter": {
          "aggregation_type": "keyword",
          "size": 100,
          "order": {
            "_key": "asc"
          },
        }
      },
      "source_index_scielo": {
        "index_field_name": "primary_location.source.scl.indexed_in",
        "filter": {
          "aggregation_type": "keyword",
          "size": 100,
          "order": {
            "_key": "asc"
          },
        }
      },
      "source_type": {
        "index_field_name": "primary_location.source.type",
        "filter": {
          "aggregation_type": "keyword",
          "size": 100,
          "order": {
            "_key": "asc"
          },
        }
      },
      "access_type": {
        "index_field_name": "open_access.oa_status",
        "filter": {
          "aggregation_type": "keyword",
          "size": 20,
          "order": {
            "_key": "asc"
          },
        }
      },
      "document_language": {
        "index_field_name": "language",
        "filter": {
          "aggregation_type": "keyword",
          "size": 200,
          "order": {
            "_key": "asc"
          },
        }
      },
      "document_type": {
        "index_field_name": "type",
        "filter": {
          "aggregation_type": "keyword",
          "size": 100,
          "order": {
            "_key": "asc"
          },
        }
      },
      "open_access": {
        "index_field_name": "open_access.is_oa",
        "filter": {
          "aggregation_type": "ignore",
          "transform": {
            "type": "boolean"
          },
          "size": 2,
          "order": {
            "_key": "asc"
          },
        }
      },
      "publication_year": {
        "index_field_name": "publication_year",
        "filter": {
          "aggregation_type": "ignore",
          "size": 100,
          "order": {
            "_key": "desc"
          },
        }
      },
      "subject_area_level_0": {
        "index_field_name": "thematic_areas.level0",
        "filter": {
          "aggregation_type": "keyword",
          "size": 10,
          "order": {
            "_key": "asc"
          },
        }
      },
      "subject_area_level_1": {
        "index_field_name": "thematic_areas.level1",
        "filter": {
          "aggregation_type": "keyword",
          "size": 20,
          "order": {
            "_key": "asc"
          },
        }
      },
      "subject_area_level_2": {
        "index_field_name": "thematic_areas.level2",
        "filter": {
          "aggregation_type": "keyword",
          "size": 50,
          "order": {
            "_key": "asc"
          },
        }
      },
      "institution": {
        "index_field_name": "authorships.institutions.display_name",
        "filter": {
          "aggregation_type": "keyword",
          "size": 1,
          "order": {
            "_key": "asc"
          },
        }
      },
      "country": {
        "index_field_name": "authorships.countries",
        "filter": {
          "aggregation_type": "keyword",
          "size": 400,
          "order": {
            "_key": "asc"
          },
          "support_query_operator": True
        }
      },
      "region_world": {
        "index_field_name": "geos.scimago_regions",
        "filter": {
          "aggregation_type": "keyword",
          "size": 20,
          "order": {
            "_key": "asc"
          },
        }
      },
      "cited_by_count": {
        "index_field_name": "cited_by_count",
        "filter": {
          "size": 10,
          "order": {
            "_key": "desc"
          },
        }
      },
      "source_country": {
        "index_field_name": "journal_metadata.country",
        "filter": {
          "aggregation_type": "keyword",
          "size": 300,
          "order": {
            "_key": "asc"
          },
        }
      },
      "source_name": {
        "index_field_name": "primary_location.source.display_name",
        "filter": {
          "aggregation_type": "keyword",
          "size": 1,
          "order": {
            "_key": "asc"
          },
        }
      },
      "issn": {
        "index_field_name": "primary_location.source.issn",
        "filter": {
          "aggregation_type": "keyword",
          "size": 1,
          "order": {
            "_key": "asc"
          },
        }
      }
    }
  },
  "scielo": {
    "index_name": settings.ES_INDEX_SCI_PROD_SCIELO,
    "display_name": _("Scientific Production - SciELO Network"),
    "field_settings": {
      "collection": {
        "index_field_name": "collection",
        "filter": {
          "aggregation_type": "keyword",
          "size": 50,
          "order": {
            "_key": "asc"
          },
        }
      },
      "publisher": {
        "index_field_name": "publisher",
        "filter": {
          "aggregation_type": "keyword",
          "size": 1,
          "order": {
            "_key": "asc"
          },
        }
      },
      "journal": {
        "index_field_name": "journal",
        "filter": {
          "aggregation_type": "keyword",
          "size": 1,
          "order": {
            "_key": "asc"
          },
        }
      },
      "access_type": {
        "index_field_name": "open_access_oa_status",
        "filter": {
          "aggregation_type": "keyword",
          "size": 20,
          "order": {
            "_key": "asc"
          },
        }
      },
      "document_language": {
        "index_field_name": "languages",
        "filter": {
          "aggregation_type": "keyword",
          "size": 500,
          "order": {
            "_key": "asc"
          },
          "support_query_operator": True
        }
      },
      "document_type": {
        "index_field_name": "type",
        "filter": {
          "size": 100,
          "order": {
            "_key": "asc"
          },
        }
      },
      "document_publication_year_start": {
        "index_field_name": "publication_year",
        "filter": {
          "transform": {
            "type": "year_range",
            "sources": [
              "document_publication_year_start",
              "document_publication_year_end",
            ]
          },
          "aggregation_type": "ignore",
          "size": 500,
          "order": {
            "_key": "asc"
          },
        }
      },
      "document_publication_year_end": {
        "index_field_name": "publication_year",
        "filter": {
          "transform": {
            "type": "year_range",
            "sources": [
              "document_publication_year_start",
              "document_publication_year_end",
            ]
          },
          "aggregation_type": "ignore",
          "size": 500,
          "order": {
            "_key": "asc"
          },
        }
      },
      "country": {
        "index_field_name": "authorships_countries",
        "aggregation_type": "keyword",
        "filter": {
          "size": 300,
          "order": {
            "_key": "asc"
          },
          "support_query_operator": True
        }
      },
      "institution": {
        "index_field_name": "authorships_institutions_display_name",
        "filter": {
          "aggregation_type": "keyword",
          "size": 1,
          "order": {
            "_key": "asc"
          },
        }
      },
      "cited_by_count": {
        "index_field_name": "openalex_cited_by_count",
        "filter": {
          "size": 10,
          "order": {
            "_key": "desc"
          },
        }
      }
    }
  },
  "social": {
    "index_name": settings.ES_INDEX_SOC_PROD,
    "display_name": _("Social Production"),
    "field_settings": {
      "document_publication_year_start": {
        "index_field_name": "year",
        "filter": {
          "transform": {
                "type": "year_range",
                "sources": [
                    "document_publication_year_start",
                    "document_publication_year_end",
                ]
          },
          "aggregation_type": "ignore",
          "size": 1000,
          "order": {
            "_key": "asc"
          },
        }
      },
      "document_publication_year_end": {
        "index_field_name": "year",
        "filter": {
            "transform": {
                "type": "year_range",
                "sources": [
                    "document_publication_year_start",
                    "document_publication_year_end",
                ]
            },
            "aggregation_type": "ignore",
            "size": 1000,
            "order": {
                "_key": "asc"
            },
        }
      },
      "city_brazil": {
        "index_field_name": "cities",
        "filter": {
          "aggregation_type": "enum",
          "size": 1000,
          "order": {
            "_key": "asc"
          },
        }
      },
      "state_brazil": {
        "index_field_name": "states",
        "filter": {
          "aggregation_type": "enum",
          "size": 27,
          "order": {
            "_key": "asc"
          },
        }
      },
      "action": {
        "index_field_name": "action",
        "filter": {
          "aggregation_type": "enum",
          "size": 1000,
          "order": {
            "_key": "asc"
          },
        }
      },
      "classification": {
        "index_field_name": "classification",
        "filter": {
          "aggregation_type": "enum",
          "size": 1000,
          "order": {
            "_key": "asc"
          },
        }
      },
      "directory_type": {
        "index_field_name": "directory_type",
        "filter": {
          "aggregation_type": "enum",
          "size": 1000,
          "order": {
            "_key": "asc"
          },
        }
      },
      "institution": {
        "index_field_name": "institutions",
        "filter": {
          "aggregation_type": "enum",
          "size": 100,
          "order": {
            "_key": "asc"
          },
        }
      },
      "practice": {
        "index_field_name": "practice",
        "filter": {
          "aggregation_type": "enum",
          "size": 1000,
          "order": {
            "_key": "asc"
          },
        }
      },
    }
  },
  "journal_metrics": {
    "index_name": settings.ES_INDEX_JOURNAL_METRICS,
    "display_name": _("Journal Metrics"),
    "field_settings": {
      "country": {
        "index_field_name": "country",
        "filter": {
          "size": 300,
          "order": {
            "_key": "asc"
          },
        }
      },
      "journal": {
        "index_field_name": "journal",
        "filter": {
          "size": 1,
          "order": {
            "_key": "asc"
          },
          "support_search_as_you_type": True
        }
      },
      "openalex_region": {
        "index_field_name": "openalex_region",
        "filter": {
          "size": 100,
          "order": {
            "_key": "asc"
          },
        }
      },
      "publisher_name": {
        "index_field_name": "publisher_name",
        "filter": {
          "size": 1,
          "order": {
            "_key": "asc"
          },
          "support_search_as_you_type": True
        }
      },
      "scielo_collection_name": {
        "index_field_name": "scielo_collection_name",
        "filter": {
          "size": 100,
          "order": {
            "_key": "asc"
          },
        }
      },
      "scielo_thematic_area": {
        "index_field_name": "scielo_thematic_areas",
        "filter": {
          "size": 50,
          "order": {
            "_key": "asc"
          },
          "support_query_operator": True
        }
      },
      "scimago_region": {
        "index_field_name": "scimago_region",
        "filter": {
          "size": 20,
          "order": {
            "_key": "asc"
          },
        }
      },
      "source_index": {
        "index_field_name": "source",
        "filter": {
          "size": 50,
          "order": {
            "_key": "asc"
          },
          "support_query_operator": True
        }
      },
      "issn": {
        "index_field_name": "issns",
        "filter": {
          "size": 1,
          "order": {
            "_key": "asc"
          },
          "support_search_as_you_type": True
        }
      },
      "year_founded": {
        "index_field_name": "year_of_creation_of_the_periodical",
        "filter": {
          "aggregation_type": "ignore",
          "size": 1000,
          "order": {
            "_key": "asc"
          },
        }
      },
      "is_scielo": {
        "index_field_name": "is_scielo",
        "filter": {
            "aggregation_type": "ignore",
            "transform": {
                "type": "boolean"
          },
          "size": 2,
          "order": {
            "_key": "asc"
          },
        }
      },
      "year": {
        "index_field_name": "year",
        "filter": {
          "aggregation_type": "ignore",
          "size": 200,
          "order": {
            "_key": "asc"
          },
        }
      },
      "cwts_snip": {
        "index_field_name": "cwts_snip",
        "filter": {
          "use": False,
          "size": 1,
          "order": {
            "_key": "desc"
          },
        }
      },
      "openalex_num_docs": {
        "index_field_name": "openalex_num_docs",
        "filter": {
          "use": False,
          "size": 1,
          "order": {
            "_key": "desc"
          },
        }
      },
      "scielo_num_docs": {
        "index_field_name": "scielo_num_docs",
        "filter": {
          "use": False,
          "size": 1,
          "order": {
            "_key": "desc"
          },
        }
      },
      "scimago_best_quartile": {
        "index_field_name": "scimago_best_quartile",
        "filter": {
          "use": False,
          "size": 1,
          "order": {
            "_key": "asc"
          },
        }
      },
      "scimago_citable_docs_3_years": {
        "index_field_name": "scimago_citable_docs_3_years",
        "filter": {
          "use": False,
          "size": 1,
          "order": {
            "_key": "desc"
          },
        }
      },
      "scimago_cites_by_doc_2_years": {
        "index_field_name": "scimago_cites_by_doc_2_years",
        "filter": {
          "use": False,
          "size": 1,
          "order": {
            "_key": "desc"
          },
        }
      },
      "scimago_estimated_apc": {
        "index_field_name": "scimago_estimated_apc",
        "filter": {
          "use": False,
          "size": 1,
          "order": {
            "_key": "desc"
          },
        }
      },
      "scimago_estimated_value": {
        "index_field_name": "scimago_estimated_value",
        "filter": {
          "use": False,
          "size": 1,
          "order": {
            "_key": "desc"
          },
        }
      },
      "scimago_female_authors_percent": {
        "index_field_name": "scimago_female_authors_percent",
        "filter": {
          "use": False,
          "size": 1,
          "order": {
            "_key": "desc"
          },
        }
      },
      "scimago_overton": {
        "index_field_name": "scimago_overton",
        "filter": {
          "use": False,
          "size": 1,
          "order": {
            "_key": "desc"
          },
        }
      },
      "scimago_sdg": {
        "index_field_name": "scimago_sdg",
        "filter": {
          "use": False,
          "size": 1,
          "order": {
            "_key": "desc"
          },
        }
      },
      "scimago_sjr": {
        "index_field_name": "scimago_sjr",
        "filter": {
          "use": False,
          "size": 1,
          "order": {
            "_key": "desc"
          },
        }
      },
      "scimago_total_cites_3_years": {
        "index_field_name": "scimago_total_cites_3_years",
        "filter": {
          "use": False,
          "size": 1,
          "order": {
            "_key": "desc"
          },
        }
      },
      "scimago_total_docs_3_years": {
        "index_field_name": "scimago_total_docs_3_years",
        "filter": {
          "use": False,
          "size": 1,
          "order": {
            "_key": "desc"
          },
        }
      }
    }
  },
  "sources": {
    "index_name": settings.ES_INDEX_SOURCES,
    "display_name": _("Sources"),
    "field_settings": {
      "source_country": {
        "index_field_name": "country",
        "filter": {
          "size": 300,
          "order": {
            "_key": "asc"
          },
        }
      },
      "source_name": {
        "index_field_name": "display_name",
        "filter": {
          "size": 1,
          "order": {
            "_key": "asc"
          },
        }
      },
      "issn": {
        "index_field_name": "issn",
        "filter": {
          "size": 1,
          "order": {
            "_key": "asc"
          },
        }
      }
    }
  }
}


def get_index_name_from_data_source(data_source):
    return DATA_SOURCES.get(data_source, {}).get("index_name")


def get_index_field_name_from_data_source(data_source, field_name):
    field_settings = get_field_settings(data_source)

    if field_name in field_settings:
        return field_settings[field_name].get("index_field_name")

    return field_name


def get_field_settings(data_source):
    return DATA_SOURCES.get(data_source, {}).get("field_settings", {})


def get_aggregation_qualified_field_name(index_field_name, filter_aggregation_type):
    if filter_aggregation_type in ("keyword", "enum"):
        return f"{index_field_name}.{filter_aggregation_type}"

    return index_field_name


def get_index_field_name_from_qualified_name(qualified_index_field_name):
    for w in ("keyword", "enum"):
        qualified_index_field_name = qualified_index_field_name.replace(f".{w}", "")

    return qualified_index_field_name


def get_query_operator_fields(data_source):
    """
    Get the fields that support query operators for a given data source.
    """
    supported_query_fields = {}
    ds_field_settings = get_field_settings(data_source)

    if not ds_field_settings:
        return {}

    for field_name, data in ds_field_settings.items():
        if data.get("filter", {}).get("support_query_operator"):
            supported_query_fields[field_name] = data.get("index_field_name")

    return supported_query_fields
