import logging
from functools import cached_property

from . import parser as response_parser
from . import query as query_builder
from .client import get_opensearch_client
from .controller import get_mapped_filters
from .models import DataSource

logger = logging.getLogger(__name__)


class SearchGatewayService:
    def __init__(self, index_name):
        self.client = get_opensearch_client()
        self._index_name = index_name

    @cached_property
    def data_source(self):
        return DataSource.objects.prefetch_related("settings_filters").get(
            index_name=self._index_name,
        )

    @property
    def index_name(self):
        return self._index_name

    @property
    def display_name(self):
        return self.data_source.display_name

    @property
    def source_fields(self):
        return self.data_source.source_fields or []

    def get_filters(self):
        return self.data_source.build_filters_query

    def get_filter_metadata(self, filters):
        return self.data_source.get_filter_metadata(filters=filters)

    def build_filters(self, body=None):
        body = body or self.get_filters()
        res = self.client.search(index=self.index_name, body=body, request_cache=True)
        return response_parser.parse_filters_response(response=res, index_name=self.index_name)

    def extract_selected_filters(self, request, available_filters):
        field_settings = self.data_source.get_field_settings_dict()
        return response_parser.extract_selected_filters(
            request, available_filters, field_settings=field_settings,
        )

    def search_documents(self, query_text=None, filters=None, page=1, page_size=10):
        field_settings = self.data_source.get_field_settings_dict()
        mapped_filters = get_mapped_filters(filters, field_settings)
        body = query_builder.build_document_search_body(
            query_text=query_text,
            filters=mapped_filters,
            page=page,
            page_size=page_size,
            source_fields=self.source_fields,
        )
        res = self.client.search(index=self.index_name, body=body)
        return response_parser.parse_document_search_response(res)

    @property
    def total_items(self):
        return self.client.count(index=self.index_name)
