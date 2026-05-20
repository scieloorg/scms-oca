from django.test import SimpleTestCase

from search_gateway.transforms import apply_display_transform


class ScopeDisplayTransformTests(SimpleTestCase):
    def test_openalex_works_label(self):
        self.assertEqual(apply_display_transform("scope", "openalex_works"), "OpenAlex")

    def test_scielo_label(self):
        self.assertEqual(apply_display_transform("scope", "scielo"), "SciELO")

    def test_unknown_scope_value_unchanged(self):
        self.assertEqual(apply_display_transform("scope", "other_source"), "other_source")

    def test_unknown_transform_type_unchanged(self):
        self.assertEqual(apply_display_transform("missing", "openalex_works"), "openalex_works")
