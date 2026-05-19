import logging
import time
from copy import deepcopy
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

    def ensure_rollover_index(
        self,
        *,
        index_prefix: str,
        write_alias: str,
        public_alias: str,
        mapping: Dict[str, Any],
    ) -> str | None:
        if self.index_exists(write_alias):
            return None

        index_name = f"{index_prefix}-000001"
        body = deepcopy(mapping)
        aliases = body.setdefault("aliases", {})
        aliases[write_alias] = {"is_write_index": True}
        aliases[public_alias] = {}

        logger.info(
            "Creating rollover bootstrap index '%s' for write alias '%s'...",
            index_name,
            write_alias,
        )
        self.client.indices.create(index=index_name, body=body)
        self.wait_for_index(index_name)
        logger.info("Rollover bootstrap index '%s' created successfully.", index_name)
        return index_name

    def rollover(
        self,
        *,
        write_alias: str,
        public_alias: str,
        max_size: str | None = None,
    ) -> str | None:
        conditions: dict[str, Any] = {}
        if max_size:
            conditions["max_size"] = max_size
        if not conditions:
            return None

        response = self.client.indices.rollover(
            alias=write_alias,
            body={"conditions": conditions},
        )
        if not response.get("rolled_over"):
            return None

        new_index = response.get("new_index")
        if new_index:
            self.add_alias(new_index, public_alias)
        return new_index

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
