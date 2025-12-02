from django import template
from django.utils.translation import gettext as _
from search_gateway.data_sources_with_settings import (
    field_allows_multiple_selection,
    get_label_by_field_name,
)

register = template.Library()


@register.filter
def get_translation_data_source(key, data_source_name):
    try:
        return get_label_by_field_name(data_source_name, key)
    except Exception as e:
        return key
    
@register.filter
def field_allows_multiple_selection_filter(key, data_source_name):
    return field_allows_multiple_selection(data_source_name, key)