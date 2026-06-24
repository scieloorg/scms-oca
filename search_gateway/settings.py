import environ

_env = environ.Env()

# OpenSearch base settings
OS_URL = _env("OS_URL", default="http://opensearch:9200")
OS_REQUEST_TIMEOUT = _env.int("OS_REQUEST_TIMEOUT", default=40)

# OpenSearch index names shared by search consumers.
OP_INDEX_SOCIAL_PRODUCTION = _env.str(
    "OP_INDEX_SOCIAL_PRODUCTION",
    default="social_production",
)
OP_INDEX_SCIENTIFIC_PRODUCTION = _env.str(
    "OP_INDEX_SCIENTIFIC_PRODUCTION",
    default="scientific_production",
)

# SearchGateway settings
SEARCH_GATEWAY_LOOKUP_SOURCE_INDEX = _env.str(
    "SEARCH_GATEWAY_LOOKUP_SOURCE_INDEX",
    default=OP_INDEX_SCIENTIFIC_PRODUCTION,
)
SEARCH_GATEWAY_LOOKUP_BATCH_SIZE = _env.int(
    "SEARCH_GATEWAY_LOOKUP_BATCH_SIZE",
    default=10000,
)
SEARCH_GATEWAY_LOOKUP_NUMBER_OF_SHARDS = _env.int(
    "SEARCH_GATEWAY_LOOKUP_NUMBER_OF_SHARDS",
    default=1,
)
SEARCH_GATEWAY_LOOKUP_NUMBER_OF_REPLICAS = _env.int(
    "SEARCH_GATEWAY_LOOKUP_NUMBER_OF_REPLICAS",
    default=0,
)
SEARCH_GATEWAY_LOOKUP_SOURCE_TYPES = _env.list(
    "SEARCH_GATEWAY_LOOKUP_SOURCE_TYPES",
    default=["journal", "conference"],
)
SEARCH_GATEWAY_ERROR_INDEX = _env.str(
    "SEARCH_GATEWAY_ERROR_INDEX",
    default="search_gateway_errors",
)

DATA_FRESHNESS_FIELDS = _env.list(
    "DATA_FRESHNESS_FIELDS",
    default=["oca_indexed_at", "updated", "created", "date"],
)
DATA_FRESHNESS_CACHE_KEY = _env.str(
    "DATA_FRESHNESS_CACHE_KEY",
    default="data_freshness:by_index",
)
DATA_FRESHNESS_CACHE_TTL = _env.int(
    "DATA_FRESHNESS_CACHE_TTL",
    default=60 * 60 * 48,
)
DATA_FRESHNESS_FALLBACK_DATE = _env.str(
    "DATA_FRESHNESS_FALLBACK_DATE",
    default="",
)
