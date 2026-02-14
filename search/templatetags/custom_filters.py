from django import template
from django.conf import settings
from iso639 import Lang
from django.utils.translation import gettext as _
from datetime import date, datetime
from django.utils.dateparse import parse_date, parse_datetime
import re
register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Retorna o valor de um dicionário usando uma chave dinâmica"""
    if dictionary is None:
        return []
    return dictionary.get(key, [])


@register.filter
def format_date_br(value):
    """Formata data string para dd/mm/aaaa."""
    if not value:
        return ""

    if isinstance(value, datetime):
        return value.strftime("%d/%m/%Y")

    if isinstance(value, date):
        return value.strftime("%d/%m/%Y")

    match = re.match(r"^(\d{4})-(\d{2})-(\d{2})", value)
    if match:
        return f"{match.group(3)}-{match.group(2)}-{match.group(1)}"

    return value
