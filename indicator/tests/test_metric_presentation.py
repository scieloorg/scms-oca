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

