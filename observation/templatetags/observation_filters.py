"""Observation template filters - for observation-specific templates."""
from django import template

register = template.Library()


@register.filter
def in_list(value, the_list):
    """Return True if value (as string) is in the_list. Handles type mismatch."""
    if the_list is None:
        return False
    return any(str(value) == str(item) for item in the_list)
