import os

from django.conf import settings
from django.utils.translation import gettext as _
from elasticsearch import Elasticsearch


ELASTICSEARCH_HOST = os.getenv("ELASTICSEARCH_HOST", "http://elasticsearch:9200")
ELASTICSEARCH_API_KEY = os.getenv("ELASTICSEARCH_API_KEY")
INDEX_NAME_ELASTICSEARCH = os.getenv("INDEX_NAME_ELASTICSEARCH", "openalex_works")


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
            if key in settings.ELASTICSEARCH_AGGREGATION_CONFIGS.keys():
                must_filters.append(
                    {"terms": {settings.ELASTICSEARCH_AGGREGATION_CONFIGS[key]["terms"]["field"]: value}}
                )
        return must_filters

    @classmethod
    def get_aggregations(cls, search_query=None, current_filters=None):
        """
        Busca agregações para popular o filtro
        Retorna contagens de cada faceta
        """
        filter_clauses = cls.build_filters(current_filters or {})
        agg_query = {
            "size": 0,  # Não retornar documentos
            "aggs": {},
        }

        for key, value in settings.ELASTICSEARCH_AGGREGATION_CONFIGS.items():
            agg_filters = {k: v for k, v in (current_filters or {}).items() if k != key}
            filter_clauses_for_agg = cls.build_filters(agg_filters)

            if search_query:
                base_query = {
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
                        "filter": filter_clauses_for_agg,
                    }
                }
            else:
                base_query = (
                    {
                        "bool": {
                            "must": {"match_all": {}},
                            "filter": filter_clauses_for_agg,
                        }
                    }
                    if filter_clauses_for_agg
                    else {"match_all": {}}
                )

            if filter_clauses_for_agg or search_query:
                agg_query["aggs"][key] = {
                    "filter": base_query,
                    "aggs": {key: {"terms": value.get("terms", {})}},
                }
            else:
                agg_query["aggs"][key] = {"terms": value.get("terms", {})}

        agg_query["query"] = {"match_all": {}}
        return agg_query


class ElasticSearchHandler:
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

    def get_filter_aggregations(search_query, selected_filters):
        """Busca agregações com filtros aplicados (excluindo cada campo na sua própria agregação)"""
        agg_query = ElasticSearchQueryObject.get_aggregations(
            search_query, selected_filters
        )
        response = client.handler_search_response(body=agg_query)
        aggregations = {}
        for key in settings.ELASTICSEARCH_AGGREGATION_CONFIGS.keys():
            if key in response["aggregations"].keys():
                agg_data = response["aggregations"][key]
                if key in agg_data:
                    aggregations[key] = agg_data[key]["buckets"]
                elif "buckets" in agg_data:
                    aggregations[key] = agg_data["buckets"]
        return aggregations


client = ElasticSearchHandler(
    index=INDEX_NAME_ELASTICSEARCH,
    api_key=ELASTICSEARCH_API_KEY,
)