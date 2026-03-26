from urllib.parse import parse_qs, urlparse

from wagtail.models import Locale, Site

from core.models import SAMenu


def build_menu(request, handle="analytics"):
    """Return the prepared menu for the current request."""
    menu = SAMenu.for_request(request, handle=handle)
    if menu is None:
        return None

    menu.render_items = list(menu.visible_items())
    prepare_menu_items(menu.render_items, request)
    return menu


def resolve_locale(language_code):
    """Return the locale for a language code."""
    return (
        Locale.objects.filter(language_code=language_code).first()
        or Locale.objects.filter(language_code__iexact=language_code).first()
    )


def get_home_url(request, locale):
    """Return the localized home URL for the current site."""
    site = Site.find_for_request(request) if request else None
    site = site or Site.objects.filter(is_default_site=True).first() or Site.objects.first()
    if site is None:
        return "/"

    root_page = site.root_page.specific
    if root_page.locale_id == locale.id:
        return root_page.url

    translated_root = root_page.get_translation_or_none(locale)
    return translated_root.url if translated_root else "/"


def get_page_url_for_language(page, locale):
    """Return the translated URL for the current page."""
    if page is None or locale is None:
        return None

    if page.locale_id == locale.id:
        return page.url

    translated_page = page.get_translation_or_none(locale)
    return translated_page.url if translated_page else None


def get_page_translation_urls(page):
    """Return translated page URLs indexed by lowercase language code."""
    if page is None:
        return {}

    translations = {page.locale.language_code.lower(): page.url}
    for translation in page.get_translations().live().specific():
        translations[translation.locale.language_code.lower()] = translation.url

    return translations


def match_request_url(request, url):
    """Return True when the current request matches the menu item URL."""
    if not request or not url:
        return False

    parsed = urlparse(url)
    target_path = parsed.path.rstrip("/") or "/"
    request_path = request.path.rstrip("/") or "/"
    if request_path != target_path and not request_path.startswith(f"{target_path}/"):
        return False

    target_query = parse_qs(parsed.query, keep_blank_values=True)
    if not target_query:
        return True

    for key, values in target_query.items():
        if sorted(request.GET.getlist(key)) != sorted(values):
            return False

    return True


def prepare_menu_items(items, request):
    """Attach render children and active state to each menu item recursively."""
    has_active_item = False

    for item in items:
        children = list(item.get_children())
        item.render_children = children
        child_active = prepare_menu_items(children, request)
        current_active = (
            item.item_type != item.ItemType.ANCHOR
            and match_request_url(request, item.resolved_url)
        )
        item.active = current_active or child_active
        has_active_item = has_active_item or item.active

    return has_active_item


def find_active_menu_path(items):
    """Return the first active branch in the prepared menu tree."""
    for item in items:
        if not getattr(item, "active", False):
            continue

        child_path = find_active_menu_path(getattr(item, "render_children", []))
        return [item] + child_path

    return []
