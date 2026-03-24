import logging
from functools import cached_property

from django.conf import settings
from opensearchpy.exceptions import ConnectionError as OpenSearchConnectionError

from .client import get_opensearch_client
from .filter_mapping import (
    apply_search_filters_to_body,
    build_filters_body,
    get_index_field_candidates,
    get_mapped_filters,
)
from .filters_cache import (
    build_filters_cache_key,
    get_cached_filters,
    store_filters_cache,
)
from .lookup import search_lookup_options, search_lookup_options_by_values
from .models import DataSource
from .query import (
    build_document_search_body,
    build_filters_aggs,
    build_keyword_contains_search_body,
    build_term_search_body,
    build_unique_items_aggregation_body,
)
from .response_parser import (
    parse_document_search_response,
    parse_filters_response,
    parse_search_item_response,
)

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

    @property
    def field_settings(self):
        return self.data_source.field_settings_dict if self.data_source else {}

    @property
    def request_timeout(self):
        return getattr(settings, "OPENSEARCH_REQUEST_TIMEOUT", 40)

    def _resolve_data_source(self):
        if not self.client:
            return None, "Service unavailable"
        if not self.data_source:
            return None, "Invalid data_source"
        return self.data_source, None

    def _search(self, body, *, index=None, **kwargs):
        return self.client.search(
            index=index or self.index_name,
            body=body,
            request_timeout=self.request_timeout,
            **kwargs,
        )

    def _resolve_field(self, field_name):
        data_source, error = self._resolve_data_source()
        if error:
            return None, error

        field = data_source.get_field(field_name)
        if not field:
            return None, "Invalid field_name"
        return field, None

    def _resolve_option_size(self, field, query_text):
        cleaned_query = str(query_text or "").strip()
        size = field.get_option_limit(default=20 if cleaned_query else 100)
        if not cleaned_query:
            return size

        max_size_with_query = getattr(settings, "SEARCH_GATEWAY_SEARCH_ITEM_MAX_SIZE", 20)
        try:
            max_size_with_query = max(1, int(max_size_with_query))
        except (TypeError, ValueError):
            max_size_with_query = 20
        return min(size, max_size_with_query)

    def _build_field_option_bodies(self, index_field_name, query_text, size):
        candidates = get_index_field_candidates(index_field_name) or [index_field_name]
        cleaned_query = str(query_text or "").strip()
        bodies = []

        if not cleaned_query:
            for candidate_field in candidates:
                bodies.append(
                    build_unique_items_aggregation_body(
                        candidate_field,
                        aggregation_size=size,
                    )
                )
            return bodies

        seen = set()
        for candidate_field in candidates:
            if candidate_field not in seen:
                bodies.append(
                    build_term_search_body(
                        candidate_field,
                        cleaned_query,
                        aggregation_size=size,
                    )
                )
                seen.add(candidate_field)

            contains_key = f"contains:{candidate_field}"
            if contains_key not in seen:
                bodies.append(
                    build_keyword_contains_search_body(
                        candidate_field,
                        cleaned_query,
                        aggregation_size=size,
                    )
                )
                seen.add(contains_key)

        return bodies

    def _search_data_source_field_options(self, field, query_text="", filters=None):
        mapped_filters = get_mapped_filters(
            filters or {},
            self.field_settings,
        )
        mapped_filters.pop(field.index_field_name, None)
        size = self._resolve_option_size(field, query_text)

        errors = []
        for body in self._build_field_option_bodies(field.index_field_name, query_text, size):
            try:
                search_body = apply_search_filters_to_body(body, mapped_filters)
                response = self._search(search_body)
                parsed = parse_search_item_response(
                    response,
                    self.data_source,
                    field.field_name,
                )
                return parsed, None
            except Exception as exc:
                errors.append(str(exc))

        if errors:
            return None, f"Error executing or parsing search: {errors[0]}"
        return [], None

    def _get_filterable_field_settings(self, *, include_fields=None, exclude_fields=None):
        field_settings = self.data_source.get_field_settings_dict(
            include_fields=include_fields,
            exclude_fields=exclude_fields,
        )
        return {
            field_name: field_info
            for field_name, field_info in field_settings.items()
            if field_info.get("kind") != "control"
        }

    def get_field_options(self, field_name, query_text="", filters=None):
        field, error = self._resolve_field(field_name)
        if error:
            return None, error

        if field.lookup and field.lookup_uses_data_source_values and field.index_field_name:
            return self._search_data_source_field_options(
                field,
                query_text=query_text,
                filters=filters,
            )

        if field.lookup:
            return search_lookup_options(
                self.client,
                field,
                query_text=query_text,
                request_timeout=self.request_timeout,
            )

        if not field.index_field_name:
            return [], None

        return self._search_data_source_field_options(
            field,
            query_text=query_text,
            filters=filters,
        )

    def get_lookup_options_by_values(self, field_name, values):
        field, error = self._resolve_field(field_name)
        if error:
            return None, error

        if not field.lookup:
            return None, "Lookup not configured"

        try:
            return search_lookup_options_by_values(
                self.client,
                self.data_source,
                field,
                values,
                request_timeout=self.request_timeout,
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
        data_source, error = self._resolve_data_source()
        if error:
            return None, error

        field_settings = self._get_filterable_field_settings(
            include_fields=include_fields,
            exclude_fields=exclude_fields,
        )
        if not field_settings:
            return {}, None

        cache_key = build_filters_cache_key(
            data_source_name=self.index_name,
            index_name=self.index_name,
            exclude_fields=exclude_fields,
            include_fields=include_fields,
            filters=filters,
            field_settings=field_settings,
        )

        cached_data = get_cached_filters(cache_key, force_refresh=force_refresh)
        if cached_data is not None:
            return cached_data, None

        aggs = build_filters_aggs(field_settings, exclude_fields)
        mapped_filters = get_mapped_filters(filters or {}, field_settings)
        body = build_filters_body(aggs, mapped_filters=mapped_filters)

        try:
            response = self._search(body)

            filters_data = parse_filters_response(
                response,
                self.data_source,
            )
            store_filters_cache(cache_key, filters_data)
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

        mapped_filters = get_mapped_filters(filters, self.field_settings)
        body = build_document_search_body(
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
            res = self._search(body, request_cache=True)
            parsed = parse_document_search_response(res)
            return parsed
        except OpenSearchConnectionError:
            logger.warning("OpenSearch unavailable while searching documents", exc_info=True)
            return {"search_results": [], "total_results": 0}
