import os
from functools import lru_cache
from urllib.parse import urlparse

from django.conf import settings
from elasticsearch import Elasticsearch
from opensearchpy import OpenSearch


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
        request_timeout=getattr(settings, "OPENSEARCH_REQUEST_TIMEOUT", 40),
    )


@lru_cache(maxsize=None)
def get_opensearch_client():
    """
    Initializes and returns a cached OpenSearch client instance.
    """
    opensearch_url = getattr(settings, "OPENSEARCH_URL", None) or os.environ.get(
        "OPENSEARCH_URL"
    )
    opensearch_url = opensearch_url or "http://localhost:9200"
    verify_certs = getattr(settings, "OPENSEARCH_VERIFY_CERTS", False)
    ca_certs = getattr(settings, "OPENSEARCH_CA_CERTS", None)
    request_timeout = getattr(settings, "OPENSEARCH_REQUEST_TIMEOUT", 40)

    parsed_url = urlparse(opensearch_url)
    host = parsed_url.hostname or "localhost"
    port = parsed_url.port or 9200
    use_ssl = parsed_url.scheme == "https"

    config = {
        "hosts": [{"host": host, "port": port}],
        "http_compress": True,
        "use_ssl": use_ssl,
        "verify_certs": verify_certs,
        "ca_certs": ca_certs,
        "timeout": request_timeout,
        "ssl_assert_hostname": False,
        "ssl_show_warn": False,
    }

    if parsed_url.username or parsed_url.password:
        config["http_auth"] = (
            parsed_url.username or "admin",
            parsed_url.password or "",
        )

    return OpenSearch(**config)
