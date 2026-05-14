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
        self.assertIn("stats", response.context)
        self.assertIn("by_type_rows", response.context["stats"])


class TriggerViewTests(EtlAdminViewTestCase):

    def test_trigger_pending_requires_post(self):
        response = self.client.get(reverse("etl_trigger_pending"))
        self.assertEqual(response.status_code, 405)

    @patch("etl.tasks.process_pending_silver_etl")
    def test_trigger_pending_dispatches_celery_task(self, mock_task):
        mock_task.delay.return_value.id = "task-456"
        response = self.client.post(reverse("etl_trigger_pending"))
        self.assertEqual(response.status_code, 302)
        mock_task.delay.assert_called_once_with(limit=5000)

    def test_trigger_pending_by_type_requires_post(self):
        response = self.client.get(reverse("etl_trigger_pending_by_type"))
        self.assertEqual(response.status_code, 405)

    @patch("etl.tasks.process_pending_silver_etl")
    def test_trigger_pending_by_type_rejects_invalid_type(self, mock_task):
        response = self.client.post(
            reverse("etl_trigger_pending_by_type"),
            {"type": "invalid"},
        )
        self.assertEqual(response.status_code, 302)
        mock_task.delay.assert_not_called()

    def test_retry_failed_by_type_requires_post(self):
        response = self.client.get(reverse("etl_retry_failed_by_type"))
        self.assertEqual(response.status_code, 405)

    def test_retry_failed_requires_post(self):
        response = self.client.get(reverse("etl_retry_failed"))
        self.assertEqual(response.status_code, 405)
