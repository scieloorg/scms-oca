from django import template

from search.models import SearchPage

register = template.Library()

@register.filter(name='startswith')
def startswith(text, starts):
    if isinstance(text, str):
        return text.startswith(starts)
    return False

@register.simple_tag()
def get_search_page(data_source_name=None):
    qs = SearchPage.objects.live()
    if data_source_name:
        qs = qs.filter(data_source__index_name=data_source_name)
    return qs.first()
