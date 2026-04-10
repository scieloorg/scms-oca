from django import template

from harvest.language_normalizer import normalize_language_field
from search.normalize import as_list, split_lang_code, unique


register = template.Library()


