import os
from functools import lru_cache
from urllib.parse import urlparse

from django.conf import settings
from opensearchpy import OpenSearch


@lru_cache(maxsize=None)
def get_opensearch_client():
    """
    Initializes and returns a cached OpenSearch client instance.
    """
    opensearch_url = getattr(settings, "OS_URL", None) or os.environ.get(
        "OS_URL"
    )
    opensearch_url = opensearch_url or "http://localhost:9200"
    verify_certs = getattr(settings, "OS_VERIFY_CERTS", False)
    ca_certs = getattr(settings, "OS_CA_CERTS", None)
    request_timeout = getattr(settings, "OS_REQUEST_TIMEOUT", 40)

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
