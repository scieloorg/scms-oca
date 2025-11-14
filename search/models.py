from django.conf import settings
from django.utils.translation import gettext as _
from wagtail.models import Page

from .elastic_search_config import ElasticSearchQueryObject, ElasticSearchHandler, client


def get_save_number(item, default: int):
    try:
        return int(item)
    except (TypeError, ValueError):
        return default


class SearchPage(Page):
    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        search_results = self.__class__._get_search_data(request)
        context.update(search_results)

        return context

    @staticmethod
    def _get_search_data(request):
        search_query = request.GET.get("search", "")
        itens_by_page = request.GET.get("itensPage", 10)

        itens_by_page = get_save_number(itens_by_page, 10)
        page_number = get_save_number(request.GET.get("page", 1), 1)

        selected_filters = SearchPage.extract_filters_from_request(request)
        from_offset = (page_number - 1) * itens_by_page

        if search_query:
            query_elastic_search = ElasticSearchQueryObject.query_multi_all_with_filters(
                search_query=search_query,
                size=itens_by_page,
                from_offset=from_offset,
                filters=selected_filters,
            )
            search_results = client.search_results(body=query_elastic_search)
        else:
            query_elastic_search = ElasticSearchQueryObject.query_match_all_with_filters(
                size=itens_by_page,
                from_offset=from_offset,
                filters=selected_filters,
            )
            search_results = client.search_results(body=query_elastic_search)

        aggregations = ElasticSearchHandler.get_filter_aggregations(
            search_query, selected_filters
        )
        total_pages = (search_results["total_results"] - 1) // itens_by_page
        has_next = page_number < total_pages
        
        return {
            "search_results": search_results["search_results"],
            "total_results": search_results["total_results"],
            "aggregations": aggregations,
            "total_pages": total_pages,
            "has_next": has_next,
            "selected_filters": selected_filters,
            "current_page": page_number,
            "has_previous": page_number > 1,
            "itens_by_page": itens_by_page,
            "search_query": search_query,
        }
    
    @staticmethod
    def extract_filters_from_request(request):
        filters = {}
        for key, config in settings.ELASTICSEARCH_AGGREGATION_CONFIGS.items():
            if value := request.GET.getlist(key):
                converter = config.get("type", str)
                if  not isinstance(converter, type):
                    converter = str
                try:
                    if converter == bool:
                        # Conversão simples de string para bool
                        filters[key] = [
                            v.lower() in ("true", "1", "yes")
                            if isinstance(v, str)
                            else bool(v)
                            for v in value
                        ]
                    else:
                        filters[key] = [converter(v) for v in value]
                except (ValueError, TypeError):
                    continue
        return filters