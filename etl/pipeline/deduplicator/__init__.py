from etl.transform.extractors import extract_doi
from etl.pipeline.deduplicator.openalex import OpenAlexMatcher
from etl.pipeline.deduplicator.scielo import SciELODeduplicator

__all__ = [
    "OpenAlexMatcher",
    "SciELODeduplicator",
    "extract_doi",
]
