from django.utils.translation import gettext as _

from . import transforms


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

def parse_search_item_response_with_transform(response, data_source, field_name):
    """
    Versão posterior a parse_search_item_response, utilizando o modelo DataSource para obter a configuração dos campos
    e aplicar as transformações de exibição.
    
    Args:
        response: Resposta do Elasticsearch contendo as agregações.
        data_source: Instância do modelo DataSource que fornece métodos para buscar configurações de campos.
        field_name: Nome do campo de interesse.

    Returns:
        Lista de dicionários contendo os buckets transformados com chave, label e doc_count.
    """
    field_settings = data_source.get_field_settings_dict()
    buckets = response.get("aggregations", {}).get("unique_items", {}).get("buckets", [])
    return [
        {
            "key": b["key"],
            "label": transforms._apply_display_transform_from_datasource(
                field_settings,
                field_name,
                b["key"],
            ),
            "doc_count": b["doc_count"],
        }
        for b in buckets
    ]


def parse_filters_response_with_transform(response, data_source):
    """
    Versão posterior a parse_filters_response, utilizando o modelo DataSource para obter a configuração dos campos
    e aplicar as transformações de exibição em todos os filtros retornados pelo Elasticsearch.

    Args:
        response: Resposta do Elasticsearch contendo as agregações.
        data_source: Instância do modelo DataSource que fornece métodos para buscar configurações de campos.

    Returns:
        Dicionário com listas de buckets filtrados, cada um contendo chave, label transformada e doc_count.
    """
    field_settings = data_source.get_field_settings_dict()
    return {
        k: [
            {
                "key": b["key"],
                "label": transforms._apply_display_transform_from_datasource(field_settings, k, b["key"]),
                "doc_count": b.get("doc_count"),
            }
            for b in v.get("buckets", [])
        ]
        for k, v in response.get("aggregations", {}).items()
    }

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
            "label": transforms.apply_transform(data_source_name, k, b["key"]),
            "doc_count": b.get("doc_count"),
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


def extract_selected_filters(request, available_filters, data_source):
    """
    Extracts filter values from the request GET parameters based on available filter keys.
    Applies value transformations (e.g., boolean) based on field settings.
    
    Args:
        request: Django request object.
        available_filters: Dict of available filter keys.
        data_source: DataSource model instance (source of field settings).
    
    Returns:
        Dict of selected filters with transformed values.
    """
    selected_filters = {}
    if not available_filters:
        return selected_filters
    
    field_settings = data_source.get_field_settings_dict()
    
    for filter_key in available_filters.keys():
        values = request.GET.getlist(filter_key)
        if values:
            cleaned_values = [v for v in values if v]
            if cleaned_values:
                field_config = field_settings.get(filter_key, {})
                transform_type = field_config.get("filter", {}).get("transform", {}).get("type")
                if transform_type == "boolean":
                    transformed_value = [_transform_boolean_value(value) for value in cleaned_values]
                    if transformed_value is not None:
                        selected_filters[filter_key] = transformed_value
                else:
                    selected_filters[filter_key] = cleaned_values
    return selected_filters
