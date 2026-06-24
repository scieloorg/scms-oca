from django.conf import settings
from django.core.cache import cache
from django.db.models import Max
from django.utils.dateparse import parse_date, parse_datetime

from core.utils.dates import epoch_ms_to_datetime
from etl.models import EtlItemProcess
from search_gateway.client import get_opensearch_client
from search_gateway.models import DataSource

CACHE_KEY = getattr(settings, "DATA_FRESHNESS_CACHE_KEY", "data_freshness:by_index")
CACHE_TTL = getattr(settings, "DATA_FRESHNESS_CACHE_TTL", 60 * 60 * 48)
SILVER_PUBLIC_ALIAS = getattr(settings, "ETL_PUBLIC_ALIAS", "silver_scientific_production")
SILVER_INDEX_PATTERN = getattr(settings, "ETL_SILVER_INDEX_PATTERN", SILVER_PUBLIC_ALIAS)
FRESHNESS_FIELDS = getattr(
    settings, "DATA_FRESHNESS_FIELDS", ["oca_indexed_at", "updated", "created", "date"]
)


def _date_from_etl_item():
    """Silver merge date: end of the ETL, from EtlItemProcess.processed_at."""
    return EtlItemProcess.objects.aggregate(value=Max("processed_at")).get("value")


def _date_from_index_document(client, index_name):
    """Latest date held in a document field of the index."""
    for field in FRESHNESS_FIELDS:
        response = client.search(
            index=index_name,
            body={"size": 0, "aggs": {"m": {"max": {"field": field}}}},
            request_cache=True,
            ignore=[400, 404],
        )
        aggregation = (response or {}).get("aggregations", {}).get("m") or {}
        value_str = aggregation.get("value_as_string")
        if value_str:
            return parse_datetime(value_str) or parse_date(value_str)
        value = epoch_ms_to_datetime(aggregation.get("value"))
        if value:
            return value
    return None

