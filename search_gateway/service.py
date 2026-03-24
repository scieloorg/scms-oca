import logging
from functools import cached_property

from django.conf import settings
from opensearchpy.exceptions import ConnectionError as OpenSearchConnectionError

from . import filters_cache
from . import lookup
from . import parser as response_parser
from . import query as query_builder
from . import utils
from .client import get_opensearch_client
from .models import DataSource

logger = logging.getLogger(__name__)


class SearchGatewayService:
    def __init__(self, index_name, client=None):
        self.client = get_opensearch_client() if client is None else client
        self._index_name = index_name

    @cached_property
    def data_source(self):
        return DataSource.get_by_index_name(index_name=self._index_name)

    @property
    def index_name(self):
        return self._index_name

    @property
    def display_name(self):
        return self.data_source.display_name if self.data_source else ""

    @property
    def source_fields(self):
        return self.data_source.source_fields or [] if self.data_source else []

    def _build_field_option_bodies(self, index_field_name, query_text, size):
        candidates = utils.get_index_field_candidates(index_field_name) or [index_field_name]
        cleaned_query = str(query_text or "").strip()
        bodies = []

        if not cleaned_query:
            for candidate_field in candidates:
                bodies.append(
                    query_builder.build_unique_items_aggregation_body(
                        candidate_field,
                        aggregation_size=size,
                    )
                )
            return bodies

        seen = set()
        for candidate_field in candidates:
            if candidate_field not in seen:
                bodies.append(
                    query_builder.build_term_search_body(
                        candidate_field,
                        cleaned_query,
                        aggregation_size=size,
                    )
                )
                seen.add(candidate_field)

            contains_key = f"contains:{candidate_field}"
            if contains_key not in seen:
                bodies.append(
                    query_builder.build_keyword_contains_search_body(
                        candidate_field,
                        cleaned_query,
                        aggregation_size=size,
                    )
                )
                seen.add(contains_key)

        return bodies

    def _search_data_source_field_options(self, settings_filter, query_text="", filters=None):
        mapped_filters = utils.get_mapped_filters(
            filters or {},
            self.data_source.get_field_settings_dict(),
        )
        mapped_filters.pop(settings_filter.index_field_name, None)
        cleaned_query = str(query_text or "").strip()
        size = settings_filter.get_option_limit(default=20 if cleaned_query else 100)
        if cleaned_query:
            max_size_with_query = getattr(settings, "SEARCH_GATEWAY_SEARCH_ITEM_MAX_SIZE", 20)
            try:
                max_size_with_query = max(1, int(max_size_with_query))
            except (TypeError, ValueError):
                max_size_with_query = 20
            size = min(size, max_size_with_query)

        errors = []
        for body in self._build_field_option_bodies(settings_filter.index_field_name, query_text, size):
            try:
                search_body = utils.apply_search_filters_to_body(body, mapped_filters)
                response = self.client.search(
                    index=self.index_name,
                    body=search_body,
                    request_timeout=getattr(settings, "OPENSEARCH_REQUEST_TIMEOUT", 40),
                )
                parsed = response_parser.parse_search_item_response(
                    response,
                    self.data_source,
                    settings_filter.field_name,
                )
                return parsed, None
            except Exception as exc:
                errors.append(str(exc))

        if errors:
            return None, f"Error executing or parsing search: {errors[0]}"
        return [], None

    def _enrich_options_with_lookup_labels(self, field_name, options):
        normalized_options = []
        values = []
        option_map = {}

        for option in options or []:
            value = str(option.get("key") or option.get("value") or "").strip()
            if not value:
                continue
            values.append(value)
            option_map[value] = dict(option)

        lookup_options, error = self.get_lookup_options_by_values(field_name, values)
        if error or not lookup_options:
            return options, error

        lookup_map = {
            str(option.get("key") or ""): option
            for option in lookup_options
            if option.get("key")
        }
        for value in values:
            base_option = dict(option_map.get(value) or {})
            lookup_option = lookup_map.get(value) or {}
            base_option["label"] = lookup_option.get("label") or base_option.get("label") or value
            normalized_options.append(base_option)
        return normalized_options, None

    def get_field_options(self, field_name, query_text="", filters=None):
        if not self.client:
            return None, "Service unavailable"
        if not self.data_source:
            return None, "Invalid data_source"

        settings_filter = self.data_source.get_field(field_name)
        if not settings_filter:
            return None, "Invalid field_name"

        lookup_config = settings_filter.get_lookup_config()
        if lookup_config:
            if (
                settings_filter.get_ui_setting("lookup_use_data_source_values")
                and not str(query_text or "").strip()
                and filters
            ):
                data_source_options, data_source_error = self._search_data_source_field_options(
                    settings_filter,
                    query_text=query_text,
                    filters=filters,
                )
                if data_source_error:
                    return None, data_source_error
                return self._enrich_options_with_lookup_labels(field_name, data_source_options)
            try:
                return lookup.search_lookup_options(
                    self.client,
                    self.data_source,
                    settings_filter,
                    query_text=query_text
                )
            except Exception as exc:
                return None, f"Error retrieving lookup options: {exc}"

        if not settings_filter.index_field_name:
            return [], None

        return self._search_data_source_field_options(
            settings_filter,
            query_text=query_text,
            filters=filters,
        )

    def get_lookup_options_by_values(self, field_name, values):
        if not self.client:
            return None, "Service unavailable"
        if not self.data_source:
            return None, "Invalid data_source"

        settings_filter = self.data_source.get_field(field_name)
        if not settings_filter:
            return None, "Invalid field_name"

        lookup_config = settings_filter.get_lookup_config()
        if not lookup_config:
            return None, "Lookup not configured"

        try:
            return lookup.search_lookup_options_by_values(
                self.client,
                self.data_source,
                settings_filter,
                values,
            )
        except Exception as exc:
            return None, f"Error retrieving lookup options: {exc}"

    def search_item(self, q, field_name, filters=None):
        results, error = self.get_field_options(
            field_name,
            query_text=q,
            filters=filters,
        )
        if error:
            return None, error
        return {"results": results or []}, None

    def get_filters_data(
        self,
        exclude_fields=None,
        include_fields=None,
        force_refresh=False,
        filters=None,
    ):
        if not self.client:
            return None, "Service unavailable"
        if not self.data_source:
            return None, "Invalid data_source"

        field_settings = self.data_source.get_field_settings_dict(
            include_fields=include_fields,
            exclude_fields=exclude_fields,
        )
        field_settings = {
            field_name: field_info
            for field_name, field_info in field_settings.items()
            if field_info.get("kind") != "control"
        }
        if not field_settings:
            return {}, None

        cache_key = filters_cache.build_filters_cache_key(
            data_source_name=self.index_name,
            index_name=self.index_name,
            exclude_fields=exclude_fields,
            include_fields=include_fields,
            filters=filters,
            field_settings=field_settings,
        )

        cached_data = filters_cache.get_cached_filters(cache_key, force_refresh=force_refresh)
        if cached_data is not None:
            return cached_data, None

        aggs = query_builder.build_filters_aggs(field_settings, exclude_fields)
        mapped_filters = utils.get_mapped_filters(filters or {}, field_settings)
        body = utils.build_filters_body(aggs, mapped_filters=mapped_filters)

        try:
            response = self.client.search(
                index=self.index_name,
                body=body,
                request_timeout=getattr(settings, "OPENSEARCH_REQUEST_TIMEOUT", 40),
            )

            filters_data = response_parser.parse_filters_response(
                response,
                self.data_source,
            )
            filters_cache.store_filters_cache(cache_key, filters_data)
            return filters_data, None
        except Exception as exc:
            return None, f"Error retrieving filters: {exc}"

    def search_documents(
        self,
        query_text=None,
        query_clauses=None,
        filters=None,
        page=1,
        page_size=10,
        sort_field=None,
        sort_order="desc",
    ):
        if not self.client or not self.data_source:
            return {"search_results": [], "total_results": 0}

        field_settings = self.data_source.get_field_settings_dict()
        mapped_filters = utils.get_mapped_filters(filters, field_settings)
        body = query_builder.build_document_search_body(
            query_text=query_text,
            query_clauses=query_clauses,
            filters=mapped_filters,
            page=page,
            page_size=page_size,
            sort_field=sort_field,
            sort_order=sort_order,
            source_fields=self.source_fields,
        )
        try:
            res = self.client.search(index=self.index_name, body=body, request_cache=True)
            parsed = response_parser.parse_document_search_response(res)
            return parsed
        except OpenSearchConnectionError:
            logger.warning("OpenSearch unavailable while searching documents", exc_info=True)
            return {"search_results": [], "total_results": 0}
