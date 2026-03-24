from django import template

from search_gateway.models import DataSource

register = template.Library()


@register.filter
def get_translation_data_source(key, data_source_name):
    try:
        data_source = DataSource.get_by_index_name(index_name=data_source_name)
        if not data_source:
            return key
        field = data_source.get_field(key)
        return field.label if field else key
    except Exception:
        return key
    
@register.filter
def field_allows_multiple_selection_filter(key, data_source_name):
    data_source = DataSource.get_by_index_name(index_name=data_source_name)
    if not data_source:
        return True
    field = data_source.get_field(key)
    return field.allows_multiple_selection if field else True
