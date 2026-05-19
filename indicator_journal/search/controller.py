from indicator_journal.search.normalizer import normalize_global_request_filters
from indicator_journal.search.query import execute_global_query
from indicator_journal.search.parser import parse_global_hits


def get_global_journal_metrics_data(index_name, request_filters):
    """
    Main entry point for fetching global journal metrics.
    Coordinates normalization, query execution, and parsing.
    """
    params = normalize_global_request_filters(request_filters)

    hits = execute_global_query(
        index_name,
        publication_year=params["publication_year"],
        ranking_metric=params["ranking_metric"],
        limit=params["limit"],
        filters=params["filters"]
    )

    ranking_data = parse_global_hits(
        hits,
        ranking_metric=params["ranking_metric"],
        publication_year=params["publication_year"]
    )

    # Combine base params and filters for the applied_filters return
    applied_filters = {
        "publication_year": params["publication_year"],
        "ranking_metric": params["ranking_metric"],
        "limit": str(params["limit"]),
        **params["filters"]
    }

    return ranking_data, applied_filters
