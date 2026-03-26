from urllib.parse import parse_qs, urlparse

from core.models import SAMenu


def build_menu(request, handle="analytics"):
    """Return the prepared menu for the current request."""
    menu = SAMenu.for_request(request, handle=handle)
    if menu is None:
        return None

    menu.render_items = list(menu.visible_items())
    prepare_menu_items(menu.render_items, request)
    return menu


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
