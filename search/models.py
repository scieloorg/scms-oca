import os
from elasticsearch import Elasticsearch
from wagtail.models import Page

ELASTICSEARCH_HOST = os.getenv("ELASTICSEARCH_HOST", "http://elasticsearch:9200")
ELASTICSEARCH_API_KEY = os.getenv("ELASTICSEARCH_API_KEY")


class SingletonElasticSearchHandler(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance
        return cls._instances[cls]


FILTERS = {
    "publication_year": {"field": "publication_year", "size": 100, "order": {"_key": "desc"}},
    "open_access_status": {"field": "open_access.oa_status.keyword", "size": 10},
    "languages": {"field": "language.keyword", "size": 100},
}


class ElasticSearchQueryObject:
    @classmethod
    def query_multi_match(
        cls,
        search_query,
        search_after=None,
        size=10,
        from_offset=0,
        filter_clauses=None,
    ):
        """
        Busca por relevancia
        """
        query = {
            "size": size,
            "from": from_offset,
            "sort": ["_score", "_doc"],
            "track_total_hits": True,
            "query": {
                "bool": {
                    "must": {
                        "multi_match": {
                            "query": search_query,
                            "fields": [
                                "_id^3",
                                "title^3",
                                "primary_location.doi^3",
                                "authorships.author.display_name^2",
                            ],
                            "type": "best_fields",
                            "tie_breaker": 0.3,
                        }
                    },
                    "filter": filter_clauses if filter_clauses else [],
                }
            },
        }

        if search_after:
            query["search_after"] = search_after

        return query

    @classmethod
    def query_match_phrase(cls, search_query, size=10):
        return {"size": size, "query": {"match_phrase": {"title": search_query}}}

    @classmethod
    def query_match_all(
        cls, size=10, search_after=None, from_offset=0, filter_clauses=None
    ):
        query = {
            "query": {"bool": {"must": {"match_all": {}}, "filter": filter_clauses}}
            if filter_clauses
            else {"match_all": {}},
            "from": from_offset,
            "size": size,
            "sort": ["_doc"],
            "track_total_hits": True,
        }
        if search_after:
            query["search_after"] = search_after
        return query

    @classmethod
    def query_match_all_with_filters(
        cls, size=10, search_after=None, from_offset=0, filters=None
    ):
        filter_clauses = cls.build_filters(filters or {})
        query = cls.query_match_all(
            size=size,
            search_after=search_after,
            from_offset=from_offset,
            filter_clauses=filter_clauses,
        )
        return query

    @classmethod
    def query_multi_all_with_filters(
        cls, search_query, size=10, search_after=None, from_offset=0, filters=None
    ):
        filter_clauses = cls.build_filters(filters or {})
        query = cls.query_multi_match(
            search_query=search_query,
            size=size,
            search_after=search_after,
            from_offset=from_offset,
            filter_clauses=filter_clauses,
        )
        return query

    @classmethod
    def build_filters(cls, filters):
        """
        Contrói os filtros do ElasticSearch
        """
        must_filters = []

        for key, value in filters.items():
            if key in FILTERS.keys():
                must_filters.append({"terms": {FILTERS[key]["field"]: value}})
        return must_filters

    @classmethod
    def get_aggregations(cls, search_query=None, current_filters=None):
        """
        Busca agregações para popular o filtro
        Retorna contagens de cada faceta
        """
        filter_clauses = cls.build_filters(current_filters or {})

        if search_query:
            query_part = {
                "bool": {
                    "must": {
                        "multi_match": {
                            "query": search_query,
                            "fields": [
                                "title^3",
                                "display_name^3",
                                "authorships.author.display_name^2",
                            ],
                        }
                    },
                    "filter": filter_clauses,
                }
            }
        else:
            query_part = (
                {"bool": {"must": {"match_all": {}}, "filter": filter_clauses}}
                if filter_clauses
                else {"match_all": {}}
            )

        agg_query = {
            "query": query_part,
            "size": 0,  # Não retornar documentos
            "aggs": {},
        }

        for key, value in FILTERS.items():
            agg_query["aggs"].update({key: {"terms": value}})
        return agg_query


class ElasticSearchHandler(metaclass=SingletonElasticSearchHandler):
    def __init__(self, index, host=ELASTICSEARCH_HOST, api_key=None):
        self.index = index
        self.client = Elasticsearch(host, api_key=api_key)

    def handler_search_response(self, body=None):
        return self.client.search(index=self.index, body=body)

    def search_results(self, body=None):
        hits = self.handler_search_response(body=body)
        transformed_hits = self._transform_search_results(hits)
        data_hits = {
            "search_results": transformed_hits,
            "total_results": hits["hits"]["total"]["value"],
            "last_sort": hits["hits"]["hits"][-1]["sort"]
            if hits["hits"]["hits"]
            else None,
        }
        return data_hits

    def _transform_search_results(self, search_results):
        transformed_hits = []
        for hit in search_results["hits"]["hits"]:
            transformed_hits.append(
                {
                    "index": hit.get("_index"),
                    "id": hit.get("_id"),
                    "source": hit.get("_source", {}),
                    "score": hit.get("_score"),
                }
            )
        return transformed_hits


client = ElasticSearchHandler(
    index="openalex_works",
    api_key=ELASTICSEARCH_API_KEY,
)


class SearchPage(Page):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.elastic_query_object = ElasticSearchQueryObject

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        search_query = request.GET.get("search", "")
        itens_by_page = request.GET.get("itensPage", 10)

        try:
            itens_by_page = int(itens_by_page)
        except (TypeError, ValueError):
            itens_by_page = 10

        try:
            page_number = int(request.GET.get("page", 1))
        except (TypeError, ValueError):
            page_number = 1

        selected_filters = self.extract_filters_from_request(request)
        from_offset = self.calculate_offset(page_number, itens_by_page)

        if search_query:
            query_elastic_search = (
                self.elastic_query_object.query_multi_all_with_filters(
                    search_query=search_query,
                    size=itens_by_page,
                    from_offset=from_offset,
                    filters=selected_filters,
                )
            )
            search_results = client.search_results(body=query_elastic_search)
        else:
            query_elastic_search = (
                self.elastic_query_object.query_match_all_with_filters(
                    size=itens_by_page,
                    from_offset=from_offset,
                    filters=selected_filters,
                )
            )
            search_results = client.search_results(body=query_elastic_search)

        aggregations = self.get_filter_aggregations(search_query, selected_filters)
        self.set_default_context(context, search_results)

        total_pages = (context["total_results"] - 1) // itens_by_page
        context["search_query"] = search_query
        context["current_page"] = page_number
        context["total_pages"] = total_pages
        context["has_previous"] = page_number > 1
        context["has_next"] = page_number < total_pages
        context["aggregations"] = aggregations
        context["itens_by_page"] = itens_by_page
        context["selected_filters"] = selected_filters

        return context

    def calculate_offset(self, page_number, itens_by_page):
        return (page_number - 1) * itens_by_page

    def set_default_context(self, context, search_results):
        context.update(search_results)

    def extract_filters_from_request(self, request):
        filters = {}
        
        for key in FILTERS.keys():
            if value := request.GET.getlist(key):
                if key == "publication_year":
                    filters[key] = [int(y) for y in value]
                else:
                    filters[key] = value

        return filters

    def get_filter_aggregations(self, search_query, selected_years):
        """Busca agregações de anos"""
        agg_query = self.elastic_query_object.get_aggregations(
            search_query, selected_years
        )
        response = client.handler_search_response(body=agg_query)
        aggregations = {}
        for key in FILTERS.keys():
            if key in response["aggregations"].keys():
                aggregations[key] = response["aggregations"][key]["buckets"]
        return aggregations
