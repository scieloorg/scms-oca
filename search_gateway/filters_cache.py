import json
import time

FILTERS_CACHE = {}
FILTERS_CACHE_TTL_SECONDS = 300


def parse_filters_cache_entry(cache_entry):
    if (
        isinstance(cache_entry, dict)
        and "data" in cache_entry
        and "cached_at" in cache_entry
    ):
        return cache_entry.get("data"), cache_entry.get("cached_at")
    return cache_entry, None


def normalize_filters_for_cache(filters):
    if not filters:
        return ()

    normalized = []
    for key, value in filters.items():
        if isinstance(value, list):
            normalized.append(
                (key, tuple(sorted(str(v) for v in value if v not in (None, ""))))
            )
        else:
            normalized.append((key, str(value)))
    return tuple(sorted(normalized))


def field_settings_cache_fingerprint(field_settings):
    if not field_settings:
        return ()

    return tuple(
        sorted(
            (
                field_name,
                (field_info or {}).get("index_field_name"),
                json.dumps(
                    ((field_info or {}).get("filter") or {}),
                    sort_keys=True,
                    default=str,
                ),
            )
            for field_name, field_info in field_settings.items()
        )
    )


def build_filters_cache_key(
    data_source_name,
    index_name,
    exclude_fields,
    include_fields,
    filters,
    field_settings,
):
    return (
        data_source_name,
        index_name,
        tuple(sorted(exclude_fields or [])),
        tuple(sorted(include_fields or [])),
        normalize_filters_for_cache(filters),
        field_settings_cache_fingerprint(field_settings),
    )


def get_cached_filters(cache_key, force_refresh=False):
    if force_refresh or cache_key not in FILTERS_CACHE:
        return None

    cached_data, cached_at = parse_filters_cache_entry(FILTERS_CACHE[cache_key])
    if cached_at is None or (time.monotonic() - cached_at) <= FILTERS_CACHE_TTL_SECONDS:
        return cached_data

    FILTERS_CACHE.pop(cache_key, None)
    return None


def store_filters_cache(cache_key, filters_data):
    FILTERS_CACHE[cache_key] = {
        "data": filters_data,
        "cached_at": time.monotonic(),
    }
