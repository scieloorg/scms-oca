import logging
import time
from typing import Any

from django.conf import settings
from django.utils import timezone

from search_gateway.client import get_opensearch_client

logger = logging.getLogger(__name__)


class OpenSearchIndexClient:
    """Small OpenSearch helper for index lifecycle and scroll operations."""

    def __init__(
        self,
        client: Any | None = None,
        host: str | None = None,
        port: int | None = None,
        use_ssl: bool = False,
        url: str | None = None,
    ):
        self.client = (
            client
            if client is not None
            else get_opensearch_client(
                url=url,
                host=host,
                port=port,
                use_ssl=use_ssl,
            )
        )

    def create_index(self, index_name: str, mapping: dict[str, Any]) -> None:
        if self.client.indices.exists(index=index_name):
            return

        logger.info("Creating OpenSearch index '%s'", index_name)
        self.client.indices.create(index=index_name, body=mapping)
        self.wait_for_index(index_name)

    def wait_for_index(self, index_name: str, timeout_seconds: int = 60) -> None:
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            if self.client.indices.exists(index=index_name):
                self.client.cluster.health(
                    index=index_name,
                    wait_for_status="yellow",
                    timeout=timeout_seconds,
                )
                return
            time.sleep(0.5)
        raise TimeoutError(f"Index '{index_name}' was not available after {timeout_seconds}s")

    def add_alias(self, index_name: str, alias_name: str) -> None:
        self.client.indices.put_alias(index=index_name, name=alias_name)

    def index_error(
        self,
        *,
        component: str,
        operation: str,
        message: str,
        error_type: str = "",
        traceback_text: str = "",
        context: dict[str, Any] | None = None,
        error_index_name: str | None = None,
        refresh: bool = False,
    ):
        index_name = error_index_name or settings.SEARCH_GATEWAY_ERROR_INDEX
        body = {
            "component": component,
            "operation": operation,
            "message": message,
            "error_type": error_type,
            "traceback": traceback_text,
            "context": context or {},
            "created_at": timezone.now().isoformat(),
        }
        return self.client.index(index=index_name, body=body, refresh=refresh)

    def scroll_all(self, index_name: str, query: dict[str, Any] | None = None, batch_size: int = 1000):
        scroll_id = None
        try:
            response = self.client.search(
                index=index_name,
                body={"query": query or {"match_all": {}}, "size": batch_size},
                scroll="5m",
            )
            scroll_id = response.get("_scroll_id")
            while True:
                hits = response["hits"]["hits"]
                if not hits:
                    break
                yield from hits
                response = self.client.scroll(scroll_id=scroll_id, scroll="5m")
                scroll_id = response.get("_scroll_id")
        finally:
            if scroll_id:
                try:
                    self.client.clear_scroll(scroll_id=scroll_id)
                except Exception:
                    logger.exception("Failed to clear OpenSearch scroll context")
