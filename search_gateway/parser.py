from django.utils.translation import gettext as _

from . import data_sources_with_settings, transforms
from indicator.search.utils import transform_boolean_yes_no

def _transform_boolean_value(value):
    """
    Transform a string value to a boolean for ES queries.
    
    Args:
        value: String value ("true", "false", "1", "0") or boolean.
    
    Returns:
        Boolean value or None if not a valid boolean representation.
    """
    if value in (True, "true", "1", 1):
        return True
    if value in (False, "false", "0", 0):
        return False
    return None


def parse_search_item_response(response, data_source_name=None, field_name=None):
    buckets = response.get("aggregations", {}).get("unique_items", {}).get("buckets", [])
    return [{
        "key": b["key"],
        "label": transforms.apply_transform(data_source_name, field_name, b["key"]),
        "doc_count": b["doc_count"]
    } for b in buckets]


def parse_filters_response(response, data_source_name=None):
    """
    Parses the response for filter aggregations.
    """
    return {
        k: [{
            "key": b["key"],
            "label": transforms.apply_transform(data_source_name, k, b["key"])
        } for b in v["buckets"]]
        for k, v in response.get("aggregations", {}).items()
    }


def parse_document_search_response(documents):
    transformed_documents = _transform_document_search_results(documents)
    data_documents = {
        "search_results": transformed_documents,
        "total_results": documents["hits"]["total"]["value"],
    }
    return data_documents


def _transform_document_search_results(search_results):
    transformed_hits = []
    for hit in search_results["hits"]["hits"]:
        transformed_hits.append(
            {
                "index": hit.get("_index"),
                "id": hit.get("_id"),
                "source": hit.get("_source", {}),
                "score": hit.get("_score"),
            }
        )
    return transformed_hits


def extract_selected_filters(request, available_filters, data_source_name=None):
    """
    Extracts filter values from the request GET parameters based on available filter keys.
    Applies value transformations (e.g., boolean) based on field settings.
    
    Args:
        request: Django request object.
        available_filters: Dict of available filter keys.
        data_source_name: Name of the data source for field settings lookup.
    
    Returns:
        Dict of selected filters with transformed values.
    """
    selected_filters = {}
    if not available_filters:
        return selected_filters
    
    field_settings = {}
    if data_source_name:
        field_settings = data_sources_with_settings.get_field_settings(data_source_name)
    
    for filter_key in available_filters.keys():
        values = request.GET.getlist(filter_key)
        if values:
            cleaned_values = [v for v in values if v]
            if cleaned_values:
                field_config = field_settings.get(filter_key, {})
                transform_type = field_config.get("filter", {}).get("transform", {}).get("type")
                if transform_type == "boolean":
                    transformed_value = [_transform_boolean_value(value)for value in cleaned_values]
                    if transformed_value is not None:
                        selected_filters[filter_key] = transformed_value
                else:
                    selected_filters[filter_key] = cleaned_values
    return selected_filters