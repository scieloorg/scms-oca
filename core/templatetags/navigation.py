from django import template

from core.utils.navigation import get_breadcrumb_context, get_language_links, get_rendered_menu

register = template.Library()


@register.simple_tag(takes_context=True)
def get_sa_menu(context, handle="analytics"):
    """Expose the prepared SciELO Analytics menu to templates."""
    request = context.get("request")
    return get_rendered_menu(request, handle=handle)


@register.simple_tag(takes_context=True)
def get_sa_breadcrumb(context, handle="analytics"):
    """Expose breadcrumb items derived from the active menu branch."""
    request = context.get("request")
    page = context.get("page")
    return get_breadcrumb_context(request, page, handle=handle)


@register.simple_tag(takes_context=True)
def get_sa_language_links(context):
    """Expose localized URLs for the language switcher."""
    request = context.get("request")
    page = context.get("page")
    return get_language_links(request, page)
