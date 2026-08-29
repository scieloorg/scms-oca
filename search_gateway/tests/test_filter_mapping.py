from django.test import SimpleTestCase

from search_gateway.filter_mapping import _map_transformed_filter


class DateYearRangeTests(SimpleTestCase):
    def test_reversed_years_map_to_complete_date_boundaries(self):
        field_info = {
            "kind": "index",
            "index_field_name": "created",
            "filter": {
                "transform": {
                    "type": "date_year_range",
                    "sources": ["creation_year_start", "creation_year_end"],
                }
            },
        }

        mapped_filter, handled_fields = _map_transformed_filter(
            "creation_year_range",
            field_info,
            {"creation_year_start": "2022", "creation_year_end": "2020"},
        )

        self.assertEqual(
            mapped_filter,
            ("created", {"gte": "2020-01-01", "lte": "2022-12-31"}),
        )
        self.assertEqual(handled_fields, {"creation_year_start", "creation_year_end"})
