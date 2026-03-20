from django import template
from django.conf import settings

from search.models import SearchPage

register = template.Library()

@register.filter(name='startswith')
def startswith(text, starts):
    if isinstance(text, str):
        return text.startswith(starts)
    return False

@register.simple_tag()
def get_menu_search_pages():
    """SearchPage instances for the main menu, keyed by settings OP_INDEX_*."""
    scientific_index = getattr(settings, "OP_INDEX_ALL_BRONZE", "sci*")
    social_index = getattr(settings, "OP_INDEX_SOC_PROD", "bronze_social_production")
    live = SearchPage.objects.live().select_related("data_source")
    return {
        "scientific": live.filter(data_source__index_name=scientific_index).first(),
        "social": live.filter(data_source__index_name=social_index).first(),
    }
