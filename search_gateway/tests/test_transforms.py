from django.test import SimpleTestCase
from django.utils.translation import activate, deactivate

from search_gateway.transforms import apply_display_transform


class ScopeDisplayTransformTests(SimpleTestCase):
    def test_openalex_works_label(self):
        self.assertEqual(apply_display_transform("scope", "openalex"), "OpenAlex")

    def test_scielo_label(self):
        self.assertEqual(apply_display_transform("scope", "scielo"), "SciELO")

    def test_unknown_scope_value_unchanged(self):
        self.assertEqual(apply_display_transform("scope", "other_source"), "other_source")

    def test_unknown_transform_type_unchanged(self):
        self.assertEqual(apply_display_transform("missing", "openalex_works"), "openalex_works")


class TranslatedBooleanTransformTests(SimpleTestCase):
    def setUp(self):
        self.addCleanup(deactivate)

    def test_boolean_transform_does_not_reuse_previous_language(self):
        activate("es")
        self.assertEqual(apply_display_transform("boolean", "true"), "Sí")
        self.assertEqual(apply_display_transform("boolean", "false"), "No")

        activate("en")
        self.assertEqual(apply_display_transform("boolean", "true"), "Yes")
        self.assertEqual(apply_display_transform("boolean", "false"), "No")
