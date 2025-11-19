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


@register.filter
def get_translation(key):
    return settings.SEARCH_FILTER_LABELS.get(key, key)


@register.filter
def translate_language(language_code):
    try:
        return _(Lang(language_code).name)
    except:
        return language_code