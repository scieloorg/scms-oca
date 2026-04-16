from urllib.parse import parse_qs, urlparse

from django.conf import settings
from wagtail.models import Locale, Site

from core.models import SAMenu


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


def get_rendered_menu(request, handle="analytics"):
    language_code = getattr(request, "LANGUAGE_CODE", None) if request else None
    locale = Locale.objects.filter(language_code__iexact=language_code).first()
    menu = SAMenu.for_locale(locale, handle=handle)
    if menu is None:
        return None

    return {"nodes": _build_menu_nodes(menu.visible_items(), request)}


def get_breadcrumb_context(request, page, handle="analytics"):
    language_code = getattr(request, "LANGUAGE_CODE", None) if request else None
    locale = Locale.objects.filter(language_code__iexact=language_code).first()
    home_url = _resolve_home_url(request, locale)
    menu = get_rendered_menu(request, handle=handle)
    if menu is None:
        return {"items": [], "is_home": bool(page and getattr(page, "depth", 0) <= 2), "home_url": home_url}

    active_path = _find_active_path(menu["nodes"])
    if not active_path:
        return {"items": [], "is_home": bool(page and getattr(page, "depth", 0) <= 2), "home_url": home_url}

    breadcrumb_items = []
    last_index = len(active_path) - 1
    for index, node in enumerate(active_path):
        is_current = index == last_index
        url = None
        if not is_current:
            link_page = node["link_page"]
            if node["item_type"] != "page" or (link_page and link_page.live):
                url = node["url"] or None

        breadcrumb_items.append({"label": node["label"], "url": url, "is_current": is_current})

    return {"items": breadcrumb_items, "is_home": False, "home_url": home_url}


def get_language_links(request, page):
    current_language = getattr(request, "LANGUAGE_CODE", "")
    translation_urls = {}
    if page is not None:
        translation_urls = {page.locale.language_code.lower(): page.url}
        for translation in page.get_translations().live().specific():
            translation_urls[translation.locale.language_code.lower()] = translation.url

    links = []
    for language_code, language_label in settings.LANGUAGES:
        locale = Locale.objects.filter(language_code__iexact=language_code).first()
        url = translation_urls.get(language_code.lower())
        if not url and locale is not None:
            url = _resolve_page_url(page, locale) or _resolve_home_url(request, locale)

        links.append(
            {
                "code": language_code,
                "label": language_label,
                "url": url or "/",
                "selected": language_code.lower() == current_language.lower(),
            }
        )

    return links


def _build_menu_nodes(items, request):
    nodes = []

    for item in items:
        children = _build_menu_nodes(item.get_children(), request)
        url = item.base_url
        if item.item_type == item.ItemType.PAGE and item.link_page:
            try:
                url = item.link_page.get_url(request=request) or item.base_url
            except Exception:
                url = item.base_url

        active = item.item_type != item.ItemType.ANCHOR and _match_request_url(request, url)
        active = active or any(child["active"] for child in children)
        nodes.append(
            {
                "label": item.resolved_label,
                "url": url,
                "children": children,
                "active": active,
                "icon_svg": item.icon_svg,
                "open_in_new_tab": item.open_in_new_tab,
                "item_type": item.item_type,
                "link_page": item.link_page,
            }
        )

    return nodes


def _match_request_url(request, url):
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


def _find_active_path(nodes):
    for node in nodes:
        if not node["active"]:
            continue

        child_path = _find_active_path(node["children"])
        return [node] + child_path

    return []
