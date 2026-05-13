import difflib
from typing import Any, Dict, List

from etl.pipeline.defaults import DocumentRules
from etl.pipeline.strategies import get_strategy


def rules_for_doc(doc: Dict[str, Any], fallback_rules: DocumentRules) -> DocumentRules:
    raw_type = doc.get("type") or doc.get("document_type")
    if not raw_type:
        return fallback_rules
    return get_strategy(str(raw_type)).rules


def can_compare(left: Dict[str, Any], right: Dict[str, Any], fallback_rules: DocumentRules) -> bool:
    return (
        rules_for_doc(left, fallback_rules).document_type
        == rules_for_doc(right, fallback_rules).document_type
    )


def rules_for_pair(left: Dict[str, Any], right: Dict[str, Any], fallback_rules: DocumentRules) -> DocumentRules:
    left_rules = rules_for_doc(left, fallback_rules)
    right_rules = rules_for_doc(right, fallback_rules)
    if left_rules.document_type != right_rules.document_type:
        raise ValueError(
            "Cannot apply one deduplication rule to different document types: "
            f"{left_rules.document_type}, {right_rules.document_type}"
        )
    return left_rules


def calculate_similarity(text1: str, text2: str) -> float:
    if not text1 or not text2:
        return 0.0
    return difflib.SequenceMatcher(None, text1.lower(), text2.lower()).ratio()


def select_primary_scielo_doc(scielo_group: List[Dict[str, Any]]) -> Dict[str, Any]:
    from etl.extractors import extract_doi, extract_scielo_id

    if len(scielo_group) == 1:
        return scielo_group[0]

    return sorted(
        scielo_group,
        key=lambda doc: (
            0 if doc.get("collection") == "scl" else 1,
            0 if extract_doi(doc) else 1,
            extract_scielo_id(doc) or "",
        ),
    )[0]
