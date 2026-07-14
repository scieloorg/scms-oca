from unittest.mock import Mock

from django.test import SimpleTestCase
from django.utils.translation import activate, deactivate

from indicator.metrics.config import MetricGroup
from indicator.metrics.presentation import MetricPresentation
from indicator.metrics.result import MetricResultBuilder


class ScopeBreakdownLegendTests(SimpleTestCase):
    def setUp(self):
        self.addCleanup(deactivate)

        self.data_source = Mock()
        self.data_source.field_settings_dict = {}
        self.data_source.metric_config_schema = {
            "displays": {
                "charts": {
                    "document_total_documents": {
                        "metric": "document_count",
                        "title": {
                            "pt": "Total de Documentos por Ano",
                            "en": "Total Documents per Year",
                        },
                        "type": "bar",
                        "order": 10,
                        "study_units": ["document"],
                    }
                }
            }
        }
        self.data_source.get_field.return_value = Mock(display_transform="scope", static_options=[])

        self.metric_group = MetricGroup.from_config(
            "document",
            {
                "time_dimension": {
                    "field": "publication_year",
                    "agg_type": "terms",
                },
                "metrics": [
                    {
                        "key": "document_count",
                        "agg": "count",
                        "label": {
                            "pt": "Documentos",
                            "en": "Documents",
                        },
                    }
                ],
            },
            breakdown_variable="scope",
        )
        self.openalex_scielo_response = {
            "aggregations": {
                "per_year": {
                    "buckets": [
                        {
                            "key": 2024,
                            "doc_count": 3,
                            "breakdown": {
                                "buckets": [
                                    {
                                        "key": "openalex",
                                        "doc_count": 2,
                                    },
                                    {
                                        "key": "scielo",
                                        "doc_count": 1,
                                    },
                                ]
                            },
                        }
                    ]
                }
            }
        }

    def test_english_scope_legend_uses_display_labels(self):
        activate("en")

        data = MetricResultBuilder(self.data_source, self.metric_group).build_from_response(
            self.openalex_scielo_response
        )
        adapted = MetricPresentation(self.data_source, self.metric_group).adapt_data(data, {"enabled": False})
        series_names = [series["name"] for series in adapted["charts"][0]["series"]]

        self.assertEqual(series_names, ["OpenAlex", "SciELO"])

    def test_relative_scope_legend_uses_display_labels(self):
        activate("en")

        data = MetricResultBuilder(self.data_source, self.metric_group).build_from_response(
            self.openalex_scielo_response
        )
        relative_metrics = {
            "enabled": True,
            "series": [
                {
                    "name": "openalex (Documentos)",
                    "breakdown_key": "openalex",
                    "data": [50],
                    "type": "document_count",
                    "metric_key": "document_count",
                },
                {
                    "name": "scielo (Documentos)",
                    "breakdown_key": "scielo",
                    "data": [25],
                    "type": "document_count",
                    "metric_key": "document_count",
                },
            ],
        }
        adapted = MetricPresentation(self.data_source, self.metric_group).adapt_data(data, relative_metrics)
        series_names = [series["name"] for series in adapted["charts"][1]["series"]]

        self.assertEqual(series_names, ["OpenAlex", "SciELO"])
