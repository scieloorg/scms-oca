from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.urls import reverse

from etl.models import EtlItemProcess, EtlPipelineConfig, EtlStatus
from etl.tests.base import EtlTestCase
from etl.wagtail_hooks import register_etl_menu


class EtlAdminViewTestCase(EtlTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.user = get_user_model().objects.create_superuser(
            username="etl-admin",
            email="etl-admin@example.org",
            password="pass",
        )

    def setUp(self):
        self.client.force_login(self.user)


class SummaryViewTests(EtlAdminViewTestCase):
    def test_summary_view_renders(self):
        response = self.client.get(reverse("etl_summary"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Resumo de ETL")
        self.assertContains(response, "Book Chapter")
        self.assertContains(response, "SciELO dedup")
        self.assertContains(response, "OpenAlex match")
        self.assertContains(response, "Match search index")
        self.assertContains(response, "silver_openalex-*")
        self.assertIn("stats", response.context)
        self.assertIn("type_rows", response.context["stats"])

    def test_summary_view_includes_non_operational_types(self):
        EtlItemProcess.objects.create(
            source_index="bronze_scielo_articles",
            external_id="S1",
            document_type="correction",
            status=EtlStatus.PENDING,
        )

        response = self.client.get(reverse("etl_summary"))

        type_rows = response.context["stats"]["type_rows"]
        correction_rows = [r for r in type_rows if r["key"] == "correction"]
        self.assertEqual(len(correction_rows), 1)
        self.assertEqual(correction_rows[0]["total"], 1)
        self.assertEqual(correction_rows[0][EtlStatus.PENDING], 1)

    def test_summary_view_formats_non_operational_type_labels(self):
        EtlItemProcess.objects.create(
            source_index="bronze_scielo_articles",
            external_id="S1",
            document_type="ahead-of-print",
            status=EtlStatus.PENDING,
        )

        response = self.client.get(reverse("etl_summary"))

        type_rows = response.context["stats"]["type_rows"]
        labels = [r["label"] for r in type_rows]
        self.assertIn("Ahead Of Print", labels)


class EtlMenuTests(EtlAdminViewTestCase):
    def test_menu_uses_enabled_pipeline_document_types(self):
        EtlPipelineConfig.objects.filter(name="dataset").update(enabled=False)

        menu_item = register_etl_menu()
        labels = [item.label for item in menu_item.menu.initial_menu_items]

        self.assertIn("Article", labels)
        self.assertIn("Book Chapter", labels)
        self.assertNotIn("Dataset", labels)
        self.assertNotIn("Correction", labels)


class TriggerViewTests(EtlAdminViewTestCase):

    @patch("etl.views.process_pending_silver_etl")
    def test_trigger_pending_by_type_rejects_invalid_type(self, mock_task):
        response = self.client.post(
            reverse("etl_trigger_pending_by_type"),
            {"type": "invalid"},
        )
        self.assertEqual(response.status_code, 302)
        mock_task.delay.assert_not_called()

    @patch("etl.views.process_pending_silver_etl")
    def test_trigger_pending_by_type_accepts_book_chapter(self, mock_task):
        mock_task.delay.return_value.id = "task-book-chapter"
        response = self.client.post(
            reverse("etl_trigger_pending_by_type"),
            {"type": "book-chapter"},
        )
        self.assertEqual(response.status_code, 302)
        mock_task.delay.assert_called_once_with(document_type="book-chapter")

    @patch("etl.views.process_pending_silver_etl")
    def test_trigger_pending_by_type_rejects_correction(self, mock_task):
        response = self.client.post(
            reverse("etl_trigger_pending_by_type"),
            {"type": "correction"},
        )
        self.assertEqual(response.status_code, 302)
        mock_task.delay.assert_not_called()

    @patch("etl.views.process_pending_silver_etl")
    def test_trigger_pending_by_type_rejects_disabled_pipeline_type(self, mock_task):
        EtlPipelineConfig.objects.filter(name="dataset").update(enabled=False)

        response = self.client.post(
            reverse("etl_trigger_pending_by_type"),
            {"type": "dataset"},
        )

        self.assertEqual(response.status_code, 302)
        mock_task.delay.assert_not_called()

    @patch("etl.views.process_pending_silver_etl")
    def test_retry_failed_by_type_accepts_book_chapter(self, mock_task):
        mock_task.delay.return_value.id = "task-book-chapter"
        response = self.client.post(
            reverse("etl_retry_failed_by_type"),
            {"type": "book-chapter"},
        )
        self.assertEqual(response.status_code, 302)
        mock_task.delay.assert_called_once_with(document_type="book-chapter")

    @patch("etl.views.process_pending_silver_etl")
    def test_trigger_pending_by_type_requires_type(self, mock_task):
        response = self.client.post(reverse("etl_trigger_pending_by_type"))
        self.assertEqual(response.status_code, 400)
        mock_task.delay.assert_not_called()

    @patch("etl.views.process_pending_silver_etl")
    def test_retry_failed_by_type_requires_type(self, mock_task):
        response = self.client.post(reverse("etl_retry_failed_by_type"))
        self.assertEqual(response.status_code, 400)
        mock_task.delay.assert_not_called()


class PermissionEnforcementTests(EtlAdminViewTestCase):
    def setUp(self):
        self.limited_user = get_user_model().objects.create_user(
            username="etl-limited",
            email="etl-limited@example.org",
            password="pass",
            is_staff=True,
        )
        access_admin = Permission.objects.get(
            content_type__app_label="wagtailadmin",
            codename="access_admin",
        )
        self.limited_user.user_permissions.add(access_admin)
        self.client.force_login(self.limited_user)

    @patch("etl.views.process_pending_silver_etl")
    def test_trigger_pending_by_type_requires_change_permission(self, mock_task):
        response = self.client.post(
            reverse("etl_trigger_pending_by_type"),
            {"type": "book-chapter"},
        )
        self.assertEqual(response.status_code, 302)
        mock_task.delay.assert_not_called()

    @patch("etl.views.process_pending_silver_etl")
    def test_retry_failed_by_type_requires_change_permission(self, mock_task):
        response = self.client.post(
            reverse("etl_retry_failed_by_type"),
            {"type": "book-chapter"},
        )
        self.assertEqual(response.status_code, 302)
        mock_task.delay.assert_not_called()
