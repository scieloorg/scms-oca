from django.test import RequestFactory, SimpleTestCase

from etl import wagtail_hooks


class EtlAdminActionTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_reset_to_pending_requires_post(self):
        response = wagtail_hooks.reset_to_pending_view(
            self.factory.get("/admin/etl/reset-pending/")
        )

        self.assertEqual(response.status_code, 405)

    def test_retry_failed_requires_post(self):
        response = wagtail_hooks.retry_failed_view(
            self.factory.get("/admin/etl/retry-failed/")
        )

        self.assertEqual(response.status_code, 405)
