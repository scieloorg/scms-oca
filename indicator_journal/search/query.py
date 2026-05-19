from search_gateway.client import get_opensearch_client
from indicator_journal.search.values import GLOBAL_METRICS_BOOL_FIELDS, GLOBAL_METRICS_TEXT_FIELDS


def _build_must_clauses(publication_year, filters):
    """Build the OpenSearch must clause list from normalized filters."""
    must = [{"term": {"publication_year": publication_year}}]

    for form_key, val in (filters or {}).items():
        if form_key in GLOBAL_METRICS_TEXT_FIELDS:
            must.append({"term": {GLOBAL_METRICS_TEXT_FIELDS[form_key]: val}})
        elif form_key in GLOBAL_METRICS_BOOL_FIELDS:
            if val in ("true", "false"):
                must.append({"term": {GLOBAL_METRICS_BOOL_FIELDS[form_key]: val == "true"}})

    return must


def execute_global_query(index_name, publication_year, ranking_metric, limit, filters):
    """Execute the global-metrics ranking query."""
    es = get_opensearch_client()

    must_clauses = _build_must_clauses(publication_year, filters)

    body = {
        "size": limit,
        "track_total_hits": True,
        "query": {"bool": {"must": must_clauses}},
        "sort": [{ranking_metric: {"order": "desc", "missing": "_last"}}],
        "collapse": {"field": "journal_id"},
    }

    response = es.search(index=index_name, body=body)
    return response.get("hits", {}).get("hits", [])
