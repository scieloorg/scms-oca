import logging
import time
from typing import Any, Dict, Optional

from search_gateway.client import get_opensearch_client

logger = logging.getLogger(__name__)


class OpenSearchClient:
    """Simplified OpenSearch client wrapper."""

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        use_ssl: bool = False,
        url: Optional[str] = None,
    ):
        self.client = get_opensearch_client(url=url, host=host, port=port, use_ssl=use_ssl)
        logger.info("Connected to OpenSearch")

    def index_exists(self, index_name: str) -> bool:
        return self.client.indices.exists(index=index_name)

    def create_index(self, index_name: str, mapping: Dict[str, Any]) -> None:
        if not self.index_exists(index_name):
            logger.info(f"Creating index '{index_name}'...")
            self.client.indices.create(index=index_name, body=mapping)
            self.wait_for_index(index_name)
            logger.info(f"Index '{index_name}' created successfully.")

    def wait_for_index(self, index_name: str, timeout_seconds: int = 60) -> None:
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            if self.index_exists(index_name):
                self.client.cluster.health(index=index_name, wait_for_status="yellow", timeout=timeout_seconds)
                return
            time.sleep(0.5)
        raise TimeoutError(f"Index '{index_name}' was not available after {timeout_seconds}s")

    def add_alias(self, index_name: str, alias_name: str) -> None:
        self.client.indices.put_alias(index=index_name, name=alias_name)

    def scroll_all(self, index_name: str, batch_size: int = 1000):
        scroll_id = None
        try:
            response = self.client.search(
                index=index_name,
                body={"query": {"match_all": {}}, "size": batch_size},
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
                    pass
