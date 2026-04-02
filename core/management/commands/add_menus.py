import json
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction
from django.urls import reverse
from wagtail.models import Locale, Site

from core.models import SAMenu, SAMenuItem


class Command(BaseCommand):
    help = "Seed/update SciELO Analytics menus from JSON, resolving translated pages and icons."

    def add_arguments(self, parser):
        parser.add_argument(
            "--data",
            default="core/fixtures/menus.json",
            help="Path to the menu JSON structure.",
        )
        parser.add_argument(
            "--handle",
            default="analytics",
            help="Menu handle to seed (default: analytics).",
        )
        parser.add_argument(
            "--icons-data",
            default="core/fixtures/icons.json",
            help="Path to the icons JSON structure.",
        )
        parser.add_argument(
            "--refresh-icons",
            action="store_true",
            help="Recompute icon_svg from icon_key for matching items.",
        )

    def load_data(self, path):
        return json.loads(Path(path).read_text(encoding="utf-8"))

    def resolve_icon_svg(self, icon_key):
        default_key = self.icons_data.get("default_key", "default")
        normalized_key = self.icons_data.get("aliases", {}).get((icon_key or "").strip().lower(), default_key)
        return self.icons_data.get("icons", {}).get(normalized_key, self.icons_data.get("icons", {}).get(default_key, ""))

    def resolve_link_url(self, item_data):
        link_url = item_data.get("link_url", "")
        if link_url:
            return link_url

        url_name = item_data.get("url_name")
        if not url_name:
            return ""

        return reverse(
            url_name,
            args=item_data.get("url_args") or None,
            kwargs=item_data.get("url_kwargs") or None,
        )

    def fetch_site(self):
        return Site.objects.filter(is_default_site=True).first() or Site.objects.first()

    def get_home_for_locale(self, site, locale):
        root_page = site.root_page.specific
        if root_page.locale_id == locale.id:
            return root_page
        
        return root_page.get_translation(locale).specific

    def resolve_locale(self, language_code):
        return Locale.objects.filter(language_code__iexact=language_code).first()

    def handle(self, *args, **options):
        data = self.load_data(options["data"])
        self.icons_data = self.load_data(options["icons_data"])
        site = self.fetch_site()
        self.refresh_icons = options["refresh_icons"]
        handle = options["handle"]
        base_translation_key = None

        for language_code, items in data.items():
            locale = self.resolve_locale(language_code)
            home = self.get_home_for_locale(site, locale)

            with transaction.atomic():
                menu = self.get_or_create_menu(handle=handle, locale=locale, base_translation_key=base_translation_key)
                if base_translation_key is None:
                    base_translation_key = menu.translation_key

                self.stdout.write(f"\nSincronizando menu {handle} para {locale.language_code}")
                self.sync_items(
                    menu=menu,
                    locale=locale,
                    items=items,
                    parent_item=None,
                    parent_page=home,
                    level=0,
                )
                self.stdout.write(self.style.SUCCESS(f"Menu sincronizado: {handle} ({locale.language_code})"))

    def get_or_create_menu(self, *, handle: str, locale: Locale, base_translation_key):
        defaults = {
            "title": "SciELO Analytics",
            "short_name": "SciELO Analytics",
            "is_active": True,
        }
        menu, created = SAMenu.objects.get_or_create(
            handle=handle,
            locale=locale,
            defaults=defaults,
        )

        changed = created
        for field, value in defaults.items():
            if getattr(menu, field) != value:
                setattr(menu, field, value)
                changed = True

        if base_translation_key and menu.translation_key != base_translation_key:
            menu.translation_key = base_translation_key
            changed = True

        if changed:
            menu.save()

        return menu

    def sync_items(self, *, menu, locale, items, parent_item=None, parent_page=None, level=0):
        kept_ids = []
        for index, item_data in enumerate(items):
            current_item, linked_page = self.sync_item(
                menu=menu,
                locale=locale,
                item_data=item_data,
                parent_item=parent_item,
                parent_page=parent_page,
                sort_order=index,
                level=level,
            )
            kept_ids.append(current_item.pk)

            children = item_data.get("children", [])
            self.sync_items(
                menu=menu,
                locale=locale,
                items=children,
                parent_item=current_item,
                parent_page=linked_page or parent_page,
                level=level + 1,
            )

        stale_items = menu.menu_items.filter(parent=parent_item)
        if kept_ids:
            stale_items = stale_items.exclude(pk__in=kept_ids)
        stale_items.delete()

    def sync_item(self, *, menu, locale, item_data, parent_item, parent_page, sort_order=0, level=0):
        item_type = item_data.get("type") or SAMenuItem.ItemType.PAGE
        label = item_data.get("text", "")
        icon_key = item_data.get("icon_key", "")
        allow_subnav = item_data.get("allow_subnav", False)
        link_page_slug = item_data.get("link_page_slug")
        link_url = self.resolve_link_url(item_data)
        link_anchor = item_data.get("link_anchor", "")

        self.stdout.write(
            "\t" * level
            + ",".join([item_type, label or "", link_page_slug or "", link_url or link_anchor or "", locale.language_code])
        )

        linked_page = None
        if item_type == SAMenuItem.ItemType.PAGE:
            linked_page = self.find_child_page(parent_page=parent_page, slug=link_page_slug, locale=locale)

        menu_item = self.find_matching_item(
            menu=menu,
            parent_item=parent_item,
            item_type=item_type,
            linked_page=linked_page,
            link_url=link_url,
            link_anchor=link_anchor,
        )
        if menu_item is None:
            menu_item = SAMenuItem(menu=menu, parent=parent_item, item_type=item_type)

        menu_item.parent = parent_item
        menu_item.sort_order = sort_order
        menu_item.label = label
        menu_item.short_label = item_data.get("short_label", "") or ""
        menu_item.item_type = item_type
        menu_item.link_page = linked_page
        menu_item.link_url = link_url or ""
        menu_item.link_anchor = link_anchor or ""
        menu_item.allow_subnav = allow_subnav
        menu_item.open_in_new_tab = item_data.get("open_in_new_tab", False)
        menu_item.is_visible = item_data.get("is_visible", True)
        menu_item.icon_key = icon_key or ""

        resolved_svg = self.resolve_icon_svg(icon_key)
        if self.refresh_icons or menu_item.icon_svg != resolved_svg:
            menu_item.icon_svg = resolved_svg

        menu_item.save()
        return menu_item, linked_page

    def find_matching_item(self, *, menu, parent_item, item_type, linked_page=None, link_url="", link_anchor=""):
        queryset = menu.menu_items.filter(parent=parent_item, item_type=item_type)
        
        if item_type == SAMenuItem.ItemType.PAGE and linked_page is not None:
            return queryset.filter(link_page=linked_page).first()
        
        if item_type == SAMenuItem.ItemType.URL:
            return queryset.filter(link_url=link_url).first()
        
        if item_type == SAMenuItem.ItemType.ANCHOR:
            return queryset.filter(link_anchor=link_anchor).first()
        
        return queryset.first()

    def find_child_page(self, parent_page, slug, locale):
        child = parent_page.get_children().get(locale=locale, slug=slug)
        return child.specific
