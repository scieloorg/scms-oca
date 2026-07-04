import json
from unittest.mock import patch

from django.test import RequestFactory, SimpleTestCase
from django.utils.translation import get_language

from indicator.views import chart_data_view


class IndicatorChartApiLanguageTests(SimpleTestCase):
    def test_uses_payload_language_when_building_chart_data(self):
        request = RequestFactory().post(
            "/api/v1/chart-data/",
            data=json.dumps({
                "data_source": "silver_scientific_production",
                "filters": {},
                "study_unit": "document",
                "language": "en",
            }),
            content_type="application/json",
        )

        with patch("indicator.views.get_indicator_data") as get_indicator_data:
            get_indicator_data.side_effect = lambda *args: ({"language": get_language(), "charts": []}, None)
            response = chart_data_view(request)

        payload = json.loads(response.content.decode())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["language"], "en")
        get_indicator_data.assert_called_once_with("silver_scientific_production", {}, "document")
