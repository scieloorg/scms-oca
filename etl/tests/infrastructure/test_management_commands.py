import json
from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from etl.models import EtlPipelineConfig
from etl.tests.base import EtlTestCase


class AddRulesCommandTests(EtlTestCase):
    def test_add_rules_creates_all_five_configs(self):
        EtlPipelineConfig.objects.all().delete()

        call_command("add_rules", stdout=StringIO())

        self.assertEqual(EtlPipelineConfig.objects.filter(enabled=True).count(), 5)
        names = list(EtlPipelineConfig.objects.values_list("name", flat=True).order_by("id"))
        self.assertIn("article", names)
        self.assertIn("book", names)
        self.assertIn("book-chapter", names)
        self.assertIn("preprint", names)
        self.assertIn("dataset", names)

    def test_add_rules_is_idempotent(self):
        call_command("add_rules", stdout=StringIO())
        count_before = EtlPipelineConfig.objects.count()

        call_command("add_rules", stdout=StringIO())
        self.assertEqual(EtlPipelineConfig.objects.count(), count_before)

    def test_add_rules_populates_rules_json(self):
        EtlPipelineConfig.objects.all().delete()
        call_command("add_rules", stdout=StringIO())

        article = EtlPipelineConfig.objects.get(name="article")
        self.assertIsInstance(article.rules, dict)
        self.assertIn("scielo_dedup_strategies", article.rules)
        self.assertIn("openalex_validation", article.rules)

    def test_add_rules_generates_valid_to_rules(self):
        EtlPipelineConfig.objects.all().delete()
        call_command("add_rules", stdout=StringIO())

        for config in EtlPipelineConfig.objects.all():
            rules = config.to_rules()
            self.assertTrue(rules["document_type"])
            self.assertIsInstance(rules["scielo_dedup_strategies"], list)
            self.assertIsInstance(rules["openalex_match_strategies"], list)

    def test_add_rules_purge_missing_removes_stale(self):
        call_command("add_rules", stdout=StringIO())
        EtlPipelineConfig.objects.create(
            name="stale",
            input_index="stale_index",
            silver_index_pattern="stale_pattern",
            input_document_kind="article",
            default_document_type="article",
        )
        self.assertEqual(EtlPipelineConfig.objects.filter(name="stale").count(), 1)

        call_command("add_rules", purge_missing=True, stdout=StringIO())
        self.assertEqual(EtlPipelineConfig.objects.filter(name="stale").count(), 0)


class ReconcileSilverEtlCommandTests(TestCase):
    def test_help_text_is_defined(self):
        from etl.management.commands.reconcile_silver_etl import Command

        self.assertIn("Recreate", Command.help)
