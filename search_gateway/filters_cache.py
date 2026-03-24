# Backward-compatible re-exports — canonical location is utils.cache
from .utils.cache import (  # noqa: F401
    build_filters_cache_key,
    get_cached_filters,
    store_filters_cache,
)
