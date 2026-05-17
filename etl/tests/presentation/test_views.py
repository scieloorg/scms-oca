from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.urls import reverse

from etl.tests.base import EtlTestCase


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
        self.assertContains(response, "ETL Summary")
        self.assertContains(response, "Book Chapters")
        self.assertContains(response, "SciELO dedup")
        self.assertContains(response, "OpenAlex match")
        self.assertIn("stats", response.context)
        self.assertIn("by_type_rows", response.context["stats"])


class TriggerViewTests(EtlAdminViewTestCase):

    @patch("etl.views.process_pending_silver_etl")
    def test_trigger_pending_dispatches_celery_task(self, mock_task):
        mock_task.delay.return_value.id = "task-456"
        response = self.client.post(reverse("etl_trigger_pending"))
        self.assertEqual(response.status_code, 302)
        mock_task.delay.assert_called_once_with()

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
    def test_retry_failed_by_type_accepts_book_chapter(self, mock_task):
        mock_task.delay.return_value.id = "task-book-chapter"
        response = self.client.post(
            reverse("etl_retry_failed_by_type"),
            {"type": "book-chapter"},
        )
        self.assertEqual(response.status_code, 302)
        mock_task.delay.assert_called_once_with(document_type="book-chapter")
