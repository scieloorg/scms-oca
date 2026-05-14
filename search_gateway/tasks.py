import logging

from django.conf import settings

from config import celery_app
from search_gateway.client import get_opensearch_client
from search_gateway.lookup import DEFAULT_LOOKUPS, LOOKUP_BUILDERS
from search_gateway.lookup.base import LookupIndexBuildService

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="[Gateway] Build lookup indices")
def build_lookup_indices_task(
    self,
    source_index=None,
    batch_size=None,
    max_docs=None,
    selected_lookups=None,
    lookup_index_overrides=None,
    max_items=None,
    **kwargs,
):
    if not source_index:
        source_index = getattr(
            settings,
            "SEARCH_GATEWAY_LOOKUP_SOURCE_INDEX",
            getattr(settings, "OP_INDEX_SCIENTIFIC_PRODUCTION", "scientific_production"),
        )
    if not batch_size:
        batch_size = getattr(settings, "SEARCH_GATEWAY_LOOKUP_BATCH_SIZE", 500)

    def progress(message):
        logger.info("[%s] %s", self.request.id, message)

    return LookupIndexBuildService(
        client=get_opensearch_client(),
        lookup_builders=LOOKUP_BUILDERS,
        source_index=source_index,
        batch_size=batch_size,
        selected_lookups=list(selected_lookups or DEFAULT_LOOKUPS),
        max_docs=max_docs,
        lookup_index_overrides=dict(lookup_index_overrides or {}),
        max_items=dict(max_items or {}),
        progress=progress,
    ).run()
