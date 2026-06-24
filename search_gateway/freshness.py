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


