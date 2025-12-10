from django import template
from django.conf import settings
from iso639 import Lang
from django.utils.translation import gettext as _
register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Retorna o valor de um dicionário usando uma chave dinâmica"""
    if dictionary is None:
        return []
    return dictionary.get(key, [])
