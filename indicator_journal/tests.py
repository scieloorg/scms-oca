from django.test import TestCase, RequestFactory
from wagtail.models import Site
from search_gateway.models import DataSource

from .models import IndicatorByCategoryPage, IndicatorGlobalPage
from .services import CategoryMetricsService, GlobalMetricsService


class CategoryMetricsServiceTestCase(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.data_source = DataSource.objects.create(
            index_name="journal_metrics_by_test",
            display_name="Test Journal Metrics",
            field_settings="{}"
        )
        self.site = Site.objects.get(is_default_site=True)
        self.root_page = self.site.root_page
        
        self.category_page = IndicatorByCategoryPage(
            title="Categorized Metrics",
            data_source=self.data_source,
            default_category_level="field",
            default_publication_year="2024"
        )
        self.root_page.add_child(instance=self.category_page)

    def test_service_initialization(self):
        request = self.factory.get('/dummy/')
        service = CategoryMetricsService(self.category_page, request)
        self.assertEqual(service.data_source, self.data_source)
        self.assertEqual(service.default_category_level, "field")
        self.assertEqual(service.default_publication_year, "2024")

class GlobalMetricsServiceTestCase(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.data_source = DataSource.objects.create(
            index_name="journal_metrics_global_test",
            display_name="Test Global Metrics",
            field_settings="{}"
        )
        self.site = Site.objects.get(is_default_site=True)
        self.root_page = self.site.root_page
        
        self.global_page = IndicatorGlobalPage(
            title="Global Metrics",
            data_source=self.data_source,
        )
        self.root_page.add_child(instance=self.global_page)

    def test_service_initialization(self):
        request = self.factory.get('/dummy/')
        service = GlobalMetricsService(self.global_page, request)
        self.assertEqual(service.data_source, self.data_source)
        
    def test_context_data(self):
        request = self.factory.get('/dummy/')
        service = GlobalMetricsService(self.global_page, request)
        context = service.get_context_data()
        self.assertTrue(context.get("is_global_metrics"))
        self.assertEqual(context.get("data_source"), "journal_metrics_global_test")
