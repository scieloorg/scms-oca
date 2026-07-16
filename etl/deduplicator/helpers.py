import difflib

from etl.transform.extractors import (
    extract_doi,
    extract_scielo_id,
)


def calculate_similarity(text1, text2):
    if not text1 or not text2:
        return 0.0
    return difflib.SequenceMatcher(None, text1.lower(), text2.lower()).ratio()


def select_primary_scielo_doc(scielo_group):
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
