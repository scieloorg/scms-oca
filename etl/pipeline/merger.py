from etl.indexing.contracts import SilverDocument
from etl.normalizers import as_list, unique


def merge(
    primary_doc: SilverDocument,
    enrichment_docs: list[SilverDocument] | None = None,
    *,
    match_strategy: str | None = None,
    match_confidence: str | None = None,
) -> SilverDocument:
    """Build a merge trace while keeping the primary source as canonical."""
    enrichment_docs = enrichment_docs or []
    data = primary_doc.to_dict()
    data.setdefault("oca_data", {})
    data["oca_data"]["scope"] = _scope_values(primary_doc, enrichment_docs)
    data["oca_data"]["merge_trace"] = {
        "primary_doc_id": primary_doc.doc_id,
        "enrichment_doc_ids": [doc.doc_id for doc in enrichment_docs],
    }
    if match_strategy:
        data["oca_data"]["match_strategy"] = match_strategy
    if match_confidence:
        data["oca_data"]["match_confidence"] = match_confidence

    return SilverDocument(**data)


def _scope_values(primary_doc: SilverDocument, enrichment_docs: list[SilverDocument]) -> list[str]:
    values = []
    values.extend(as_list((primary_doc.oca_data or {}).get("scope")))
    for doc in enrichment_docs:
        values.extend(as_list((doc.oca_data or {}).get("scope")))
    return unique(values)


__all__ = ["merge"]
