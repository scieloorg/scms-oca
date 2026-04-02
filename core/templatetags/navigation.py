from django.conf import settings
from django import template
from wagtail.models import Locale, Site

from core.models import SAMenu

register = template.Library()


@register.simple_tag(takes_context=True)
def get_sa_menu(context, handle="analytics"):
    """Expose the prepared SciELO Analytics menu to templates."""
    request = context.get("request")
    return build_menu(request, handle=handle)


@register.simple_tag(takes_context=True)
def get_sa_breadcrumb(context, handle="analytics"):
    """Expose breadcrumb items derived from the active menu branch."""
    request = context.get("request")
    page = context.get("page")
    current_language = getattr(request, "LANGUAGE_CODE", None)
    current_locale = resolve_locale(current_language) if current_language else None
    home_url = get_home_url(request, current_locale) if current_locale else "/"
    menu = build_menu(request, handle=handle)
    if menu is None:
        return {
            "items": [],
            "is_home": bool(page and getattr(page, "depth", 0) <= 2),
            "home_url": home_url,
        }

    active_path = find_active_menu_path(getattr(menu, "render_items", []))
    if active_path:
        return {
            "home_url": home_url,
            "is_home": False,
            "items": [
                {
                    "label": item.resolved_label,
                    "url": None if index == len(active_path) - 1 else item.resolved_url,
                }
                for index, item in enumerate(active_path)
            ]
        }

    return {
        "items": [],
        "is_home": bool(page and getattr(page, "depth", 0) <= 2),
        "home_url": home_url,
    }


@register.simple_tag(takes_context=True)
def get_sa_language_links(context):
    """Expose localized URLs for the language switcher."""
    request = context.get("request")
    page = context.get("page")
    current_language = getattr(request, "LANGUAGE_CODE", "")
    page_translation_urls = get_page_translation_urls(page)
    links = []

    for language_code, language_label in settings.LANGUAGES:
        locale = resolve_locale(language_code)
        url = page_translation_urls.get(language_code.lower())

        if not url and locale is not None:
            url = get_page_url_for_language(page, locale) or get_home_url(request, locale)

        links.append(
            {
                "code": language_code,
                "label": language_label,
                "url": url or "/",
                "selected": language_code.lower() == current_language.lower(),
            }
        )

    return links
