import re

from search.choices import QUERY_STRING_FIELD_ALIASES, SEARCH_FIELD_MAPPING, QUERY_STRING_FIELDS

def query_filters(filters):
    """
    Build filter clauses for Elasticsearch query.

    Note: Filters should already have Elasticsearch field names as keys
    (i.e., already mapped from form field names).

    Args:
        filters: Dict of filters with Elasticsearch field names as keys.

    Returns:
        List of filter clauses for the bool query.
    """
    if not filters:
        return []

    filters_clauses = []
    for f_field, f_value in filters.items():
        if isinstance(f_value, list):
            filters_clauses.append({"terms": {f_field: f_value}})
        else:
            filters_clauses.append({"term": {f_field: f_value}})
    return filters_clauses


def build_search_as_you_type_body(field_name, field_autocomplete, query, agg_size=20, add_keyword_term=False):
    """
    Builds the body for a search-as-you-type query.

    Args:
        field_name: The Elasticsearch field name to search in.
        query: The search query text.
        agg_size: Maximum number of aggregation results.

    Returns:
        Elasticsearch query body dict.
    """

    body = {
        "size": 0,
        "query": {
            "multi_match": {
                "query": query,
                "type": "bool_prefix",
                "fields": [
                    f"{field_autocomplete}",
                    f"{field_autocomplete}._2gram",
                    f"{field_autocomplete}._3gram",
                ],
            }
        },
        "aggs": {
            "unique_items": {
                "terms": {"field": field_name, "size": agg_size}
            }
        },
    }
    return body


def build_term_search_body(field_name, query, aggregation_size=20):
    """
    Builds the body for a term-based search query.

    Args:
        field_name: The Elasticsearch field name to search in.
        query: The search query text.
        aggregation_size: Maximum number of aggregation results.

    Returns:
        Elasticsearch query body dict.
    """
    if field_name.endswith(".keyword"):
        query_field = field_name[:-8]
        agg_field = field_name
    else:
        query_field = field_name
        agg_field = field_name

    return {
        "size": 0,
        "query": {"match_phrase_prefix": {query_field: query}},
        "aggs": {
            "unique_items": {
                "terms": {
                    "field": agg_field,
                    "size": aggregation_size,
                }
            }
        },
    }


def build_keyword_contains_search_body(field_name, query, aggregation_size=20):
    """
    Builds a contains search body for keyword fields using wildcard.
    """
    cleaned_query = (query or "").strip()
    if not cleaned_query:
        return {
            "size": 0,
            "query": {"match_all": {}},
            "aggs": {
                "unique_items": {
                    "terms": {"field": field_name, "size": aggregation_size}
                }
            },
        }

    escaped_query = cleaned_query.replace("\\", "\\\\").replace("*", "\\*").replace("?", "\\?")

    return {
        "size": 0,
        "query": {
            "wildcard": {
                field_name: {
                    "value": f"*{escaped_query}*",
                    "case_insensitive": True,
                }
            }
        },
        "aggs": {
            "unique_items": {
                "terms": {"field": field_name, "size": aggregation_size}
            }
        },
    }


def build_filters_aggs(field_settings, exclude_fields=None):
    """
    Builds the aggregations for retrieving filter options.

    Args:
        field_settings: Dict of field settings from data source configuration.
        exclude_fields: List of field names to exclude from aggregations.

    Returns:
        Dict of aggregation definitions.
    """
    exclude_fields = exclude_fields or []
    aggs = {}

    for form_field_name, field_info in field_settings.items():
        if form_field_name in exclude_fields:
            continue

        if field_info.get("filter", {}).get("use") is False:
            continue

        fl_name = field_info.get("index_field_name")
        if not fl_name:
            continue
        
        fl_size = field_info.get("filter", {}).get("size", 1)
        fl_order = field_info.get("filter", {}).get("order")

        terms = {"field": fl_name, "size": fl_size}
        if fl_order:
            terms["order"] = fl_order

        aggs[form_field_name] = {"terms": terms}

    return aggs



def _is_advanced_query(text):
    """Detect if text contains advanced query syntax (field:value, OR, AND, parentheses)."""
    if not text or not isinstance(text, str):
        return False
    t = text.strip()
    if re.search(r"\w+:\S+", t):
        return True
    if re.search(r"\b(OR|AND|NOT)\b", t, re.IGNORECASE):
        return True
    if "(" in t or ")" in t:
        return True
    return False


def _rewrite_field_aliases_in_query(query_text):
    """Rewrite user-friendly field names to index field names in the query string."""
    result = query_text
    for alias, index_field in sorted(
        QUERY_STRING_FIELD_ALIASES.items(), key=lambda x: -len(x[0])
    ):
        result = re.sub(
            rf"\b{re.escape(alias)}\s*:",
            f"{index_field}:",
            result,
            flags=re.IGNORECASE,
        )
    return result


def _build_advanced_query(query_text):
    """Build a query_string query for advanced syntax like (title:covid OR abstract:covid)."""
    rewritten = _rewrite_field_aliases_in_query(query_text)
    return {
        "query_string": {
            "query": rewritten,
            "fields": QUERY_STRING_FIELDS,
            "default_operator": "AND",
        }
    }


def _build_clause_query(field_key, query_text):
    """Build a clause for a given field and text. Uses query_string if advanced syntax detected."""
    if _is_advanced_query(query_text):
        return _build_advanced_query(query_text)
    fields = SEARCH_FIELD_MAPPING.get(field_key, ["title_search", "ids_search"])
    return {
        "simple_query_string": {
            "query": query_text,
            "default_operator": "AND",
            "fields": fields,
        }
    }


def _normalize_query_clauses(query_clauses):
    """Return only valid clauses, with normalized operators."""
    normalized = []

    for clause in query_clauses or []:
        text = (clause.get("text") or "").strip()
        if not text:
            continue

        normalized.append(
            {
                "operator": "" if not normalized else (clause.get("operator") or "AND").upper(),
                "query": _build_clause_query(clause.get("field") or "all", text),
            }
        )

    return normalized


def _group_or_clauses(clauses):
    """Group consecutive OR clauses into a single logical unit."""
    groups = []

    for clause in clauses:
        operator = clause["operator"]
        query = clause["query"]

        if not groups:
            groups.append({"operator": "", "queries": [query]})
            continue

        if operator == "OR":
            groups[-1]["queries"].append(query)
            continue

        groups.append({"operator": operator, "queries": [query]})

    return groups


def _build_or_group_query(queries):
    """Convert an OR group into a single OpenSearch query."""
    if len(queries) == 1:
        return queries[0]

    return {
        "bool": {
            "should": queries,
            "minimum_should_match": 1,
        }
    }


def build_bool_from_clauses(query_clauses):
    """
    Build a bool query from normalized groups of clauses.

    Consecutive OR clauses become one group. Each group is converted to either:
    - a single query, or
    - a bool/should query with minimum_should_match=1

    Then the group is appended to must or must_not according to the
    operator that precedes it.
    """
    normalized_clauses = _normalize_query_clauses(query_clauses)
    if not normalized_clauses:
        return {"must": [{"match_all": {}}]}

    bool_query = {"must": [], "must_not": []}

    for group in _group_or_clauses(normalized_clauses):
        group_query = _build_or_group_query(group["queries"])
        target = "must_not" if group["operator"] == "NOT" else "must"
        bool_query[target].append(group_query)

    if not bool_query["must"] and not bool_query["must_not"]:
        return {"must": [{"match_all": {}}]}

    if not bool_query["must"]:
        bool_query["must"].append({"match_all": {}})

    return bool_query


def build_search_text_body(query_text):
    """
    Builds a simple text search query body.

    Args:
        query_text: The search query text.

    Returns:
        Elasticsearch query body dict.
    """
    return {
        "query": {
            "simple_query_string": {
                "query": query_text,
                "default_operator": "AND",
            }
        }
    }


def build_document_search_body(
        query_text=None,
        query_clauses=None,
        filters=None,
        page=1,
        page_size=10,
        sort_field=None,
        sort_order="asc",
        source_fields=None,
):
    """
    Builds the body for a document search query with text and filters.

    Args:
        query_text: Text to search for (legacy, used when query_clauses is empty).
        query_clauses: List of {operator, field, text} for advanced search.
        filters: Dict of filters (should already be mapped to ES field names).
        page: Page number (1-based).
        page_size: Number of results per page.
        sort_field: Field to sort by.
        sort_order: Sort order ('asc' or 'desc').
        source_fields: List of fields to include in results.

    Returns:
        Elasticsearch query body dict.
    """
    if query_clauses:
        bool_query = build_bool_from_clauses(query_clauses)
    else:
        bool_query = {"must": []}
        if query_text:
            bool_query["must"].append(
                {
                    "simple_query_string": {
                        "query": query_text,
                        "default_operator": "AND",
                        "fields": ["title_search", "ids_search"],
                    }
                }
            )
        else:
            bool_query["must"].append({"match_all": {}})

    if filters:
        bool_query["filter"] = query_filters(filters)

    start = (page - 1) * page_size

    body = {
        "from": start,
        "size": page_size,
        "track_total_hits": True,
        "query": {"bool": bool_query},
    }

    if source_fields:
        body["_source"] = source_fields

    if sort_field:
        body["sort"] = [{sort_field: {"order": sort_order}}]

    return body
