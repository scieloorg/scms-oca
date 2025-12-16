from django import template
from search.models import SearchPage

register = template.Library()

@register.filter(name='startswith')
def startswith(text, starts):
    if isinstance(text, str):
        return text.startswith(starts)
    return False

@register.simple_tag()
def get_search_page():
    return SearchPage.objects.live().first()