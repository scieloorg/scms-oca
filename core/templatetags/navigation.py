from django.conf import settings
from django import template
from wagtail.models import Locale, Site

from core.models import SAMenu

register = template.Library()


def _get_locale(language_code):
    return Locale.objects.filter(language_code__iexact=language_code).first()


def _get_rendered_menu(request, handle="analytics"):
    menu = SAMenu.for_request(request, handle=handle)
    return menu.build_render_tree(request) if menu else None


def _resolve_home_url(request, locale):
    site = Site.find_for_request(request) if request else None
    site = site or Site.objects.filter(is_default_site=True).first() or Site.objects.first()
    if site is None or locale is None:
        return "/"

    root_page = site.root_page.specific
    if root_page.locale_id == locale.id:
        return root_page.url

    translated_root = root_page.get_translation_or_none(locale)
    return translated_root.url if translated_root else "/"


def _resolve_page_url(page, locale):
    if page is None or locale is None:
        return None

    if page.locale_id == locale.id:
        return page.url

    translated_page = page.get_translation_or_none(locale)
    return translated_page.url if translated_page else None


def _collect_page_translation_urls(page):
    if page is None:
        return {}

    translations = {page.locale.language_code.lower(): page.url}
    for translation in page.get_translations().live().specific():
        translations[translation.locale.language_code.lower()] = translation.url

    return translations


def _active_branch(items):
    for item in items:
        if not getattr(item, "active", False):
            continue

        child_path = _active_branch(getattr(item, "render_children", []))
        return [item] + child_path

    return []


def _breadcrumb_item_url(item):
    if item.item_type == item.ItemType.PAGE:
        link_page = getattr(item, "link_page", None)
        if not link_page or not link_page.live:
            return None

    return item.resolved_url or None


def _breadcrumb_context(page, home_url, items):
    is_home = bool(page and getattr(page, "depth", 0) <= 2)
    return {"items": items, "is_home": is_home and not items, "home_url": home_url}


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
