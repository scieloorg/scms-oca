import logging

from . import data_sources_with_settings
from . import parser as response_parser
from . import query as query_builder
from .client import get_es_client

logger = logging.getLogger(__name__)


class SearchGatewayService:
    def __init__(self, data_source_name, exclude_filter_fields=None):
        self.client = get_es_client()
        self.data_source_name = data_source_name
        self._data_source = data_sources_with_settings.get_data_source(data_source_name=data_source_name)
        self._field_settings = data_sources_with_settings.get_field_settings(data_source=data_source_name)
        self._index_name = data_sources_with_settings.get_index_name_from_data_source(data_source=data_source_name)
        self._display_fields = data_sources_with_settings.get_display_fields(data_source=data_source_name)
        self._exclude_filter_fields = exclude_filter_fields if exclude_filter_fields else []

    @property
    def data_source(self):
        return self.data_source_name

    @property
    def index_name(self):
        """Get the Elasticsearch index name"""
        return self._index_name

    @property
    def display_fields(self):
        return self._display_fields

    def get_filters(self, exclude_fields=None):
        aggs = query_builder.build_filters_aggs(self._field_settings, exclude_fields)
        body = {"size": 0, "aggs": aggs}
        return body

    def get_filter_metadata(self, filters):
        """
        Get metadata for filters (class_filter, label, etc.).
        
        Args:
            filters: Dict of available filters.
        
        Returns:
            Dict with filter metadata for each filter field.
        """
        filter_metadata = {}
        for field_name in filters.keys():
            if field_name in self._field_settings:
                filter_metadata[field_name] = self._field_settings[field_name].get("settings", {})
        return filter_metadata

    def build_filters(self, body=None):
        body = body or self.get_filters()
        res = self.client.search(index=self.index_name, body=body)
        return response_parser.parse_filters_response(res, self.data_source)


