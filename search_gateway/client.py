from functools import lru_cache
from urllib.parse import urlparse

from django.conf import settings
from elasticsearch import Elasticsearch


@lru_cache(maxsize=None)
def get_es_client():
    """
    Initializes and returns a cached Elasticsearch client instance.

    The client is created only on the first call, and subsequent calls return
    the cached instance. This avoids issues with Django settings initialization
    order.
    """
    try:
        es_config = settings.HAYSTACK_CONNECTIONS["es"]
        es_url = es_config["URL"]
        es_kwargs = es_config.get("KWARGS", {})
    except (KeyError, AttributeError):
        # Handle cases where settings are not configured as expected
        return None

    parsed_url = urlparse(es_url)

    # Use credentials from the URL or fall back to defaults.
    # The `http_auth` parameter takes precedence over credentials embedded in the URL.
    username = parsed_url.username or "elastic"
    password = parsed_url.password or ""

    # Pass the original URL directly to the client to avoid issues with
    # manual reconstruction (e.g., missing ports).
    return Elasticsearch(
        [es_url],
        http_auth=(username, password),
        verify_certs=es_kwargs.get("verify_certs", False),
        ca_certs=es_kwargs.get("ca_certs"),
    )
