from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Retorna o valor de um dicionário usando uma chave dinâmica"""
    if dictionary is None:
        return []
    return dictionary.get(key, [])