from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel
from wagtail.admin.panels import FieldPanel, InlinePanel
from wagtail.models import Locale, Orderable, Page, TranslatableMixin

from core.utils import utils

User = get_user_model()


class CommonControlField(models.Model):
    """
    Class with common control fields.

    Fields:
        created: Date time when the record was created
        updated: Date time with the last update date
        creator: The creator of the record
        updated_by: Store the last updator of the record
    """

    # Creation date
    created = models.DateTimeField(verbose_name=_("Creation date"), auto_now_add=True)

    # Update date
    updated = models.DateTimeField(verbose_name=_("Last update date"), auto_now=True)

    # Creator user
    creator = models.ForeignKey(
        User,
        verbose_name=_("Creator"),
        related_name="%(class)s_creator",
        editable=False,
        on_delete=models.CASCADE,
    )

    # Last modifier user
    updated_by = models.ForeignKey(
        User,
        verbose_name=_("Updater"),
        related_name="%(class)s_last_mod_user",
        editable=False,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )

    class Meta:
        abstract = True


class Source(models.Model):
    name = models.CharField(_("Source Name"), max_length=50, null=True, blank=True)

    autocomplete_search_field = "name"

    def autocomplete_label(self):
        return str(self)

    def __unicode__(self):
        return self.__str__()

    def __str__(self):
        return self.name or ""


class Language(models.Model):
    """
    Represent languages

    Fields:
        name: The name of the language in Inglish.
        code2: The ISO_639-1 of the language, see: https://en.wikipedia.org/wiki/ISO_639-1
    """

    name = models.TextField(_("Language Name"), blank=True, null=True)
    code2 = models.TextField(_("Language code 2"), blank=True, null=True)

    autocomplete_search_field = "code2"

    def autocomplete_label(self):
        return str(self)

    class Meta:
        verbose_name = _("Language")
        verbose_name_plural = _("Languages")

    def __unicode__(self):
        return self.code2 or "idioma ausente / não informado"

    def __str__(self):
        return self.code2 or "idioma ausente / não informado"

    @classmethod
    def get_or_create(cls, name=None, code2=None):
        code2 = utils.language_iso(code2)
        if code2:
            try:
                return cls.objects.get(code2=code2)
            except cls.DoesNotExist:
                pass

        if name:
            try:
                return cls.objects.get(name=name)
            except cls.DoesNotExist:
                pass

        if name or code2:
            obj = Language()
            obj.name = name
            obj.code2 = code2 or ""
            obj.save()
            return obj


class SAMenu(TranslatableMixin, ClusterableModel):
    title = models.CharField(max_length=255)
    handle = models.CharField(max_length=100, default="analytics")
    short_name = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)

    panels = [
        FieldPanel("title"),
        FieldPanel("handle"),
        FieldPanel("short_name"),
        FieldPanel("is_active"),
        InlinePanel("menu_items", label="Menu items"),
    ]

    class Meta(TranslatableMixin.Meta):
        verbose_name = "SciELO Analytics menu"
        verbose_name_plural = "SciELO Analytics menus"
        constraints = [
            models.UniqueConstraint(
                fields=["locale", "handle"],
                name="core_samenu_unique_handle_locale",
            ),
        ]

    def __str__(self):
        return self.short_name or self.title or self.handle

    def root_items(self):
        return self.menu_items.filter(parent__isnull=True).select_related("link_page").order_by("sort_order", "pk")

    def visible_items(self):
        return self.root_items().filter(is_visible=True)

    @classmethod
    def for_request(cls, request, handle="analytics"):
        queryset = cls.objects.filter(handle=handle, is_active=True)
        if request is None:
            return queryset.first()

        language_code = getattr(request, "LANGUAGE_CODE", None)
        locale = (
            Locale.objects.filter(language_code__iexact=language_code).first()
            if language_code
            else None
        )

        if locale is not None:
            return queryset.filter(locale=locale).first() or queryset.first()

        return queryset.first()


class SAMenuItem(Orderable):
    class ItemType(models.TextChoices):
        PAGE = "page", "Page"
        URL = "url", "URL"
        ANCHOR = "anchor", "Anchor"

    menu = ParentalKey("core.SAMenu", on_delete=models.CASCADE, related_name="menu_items")
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        related_name="child_menu_items",
        null=True,
        blank=True,
    )
    label = models.CharField(max_length=255)
    short_label = models.CharField(max_length=100, blank=True)
    item_type = models.CharField(max_length=20, choices=ItemType.choices, default=ItemType.PAGE)
    link_page = models.ForeignKey(
        Page,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    link_url = models.CharField(max_length=500, blank=True)
    link_anchor = models.CharField(max_length=255, blank=True)
    allow_subnav = models.BooleanField(default=False)
    open_in_new_tab = models.BooleanField(default=False)
    is_visible = models.BooleanField(default=True)
    icon_key = models.CharField(max_length=100, blank=True)
    icon_svg = models.TextField(blank=True)

    panels = [
        FieldPanel("parent"),
        FieldPanel("label"),
        FieldPanel("short_label"),
        FieldPanel("item_type"),
        FieldPanel("link_page"),
        FieldPanel("link_url"),
        FieldPanel("link_anchor"),
        FieldPanel("icon_key"),
        FieldPanel("icon_svg"),
        FieldPanel("allow_subnav"),
        FieldPanel("open_in_new_tab"),
        FieldPanel("is_visible"),
    ]

    class Meta:
        verbose_name = "SciELO Analytics menu item"
        verbose_name_plural = "SciELO Analytics menu items"
        constraints = [
            models.CheckConstraint(
                condition=~Q(parent=models.F("pk")),
                name="core_samenuitem_parent_not_self",
            ),
        ]

    def __str__(self):
        return self.label

    def get_children(self, *, visible_only=True):
        if not self.allow_subnav:
            return self.menu.menu_items.none()

        queryset = self.menu.menu_items.filter(parent=self)

        if visible_only:
            queryset = queryset.filter(is_visible=True)

        return queryset.select_related("link_page").order_by("sort_order", "pk")

    @property
    def resolved_label(self):
        if self.item_type == self.ItemType.URL:
            return self.label or self.link_url

        if self.item_type == self.ItemType.ANCHOR:
            return self.label or self.link_anchor

        return self.label or getattr(self.link_page, "title", "")

    @property
    def resolved_url(self):
        if self.item_type == self.ItemType.PAGE and self.link_page:
            try:
                return self.link_page.url or self.link_page.get_url()
            except Exception:
                return getattr(self.link_page, "url", "")

        if self.item_type == self.ItemType.URL:
            return self.link_url

        anchor = (self.link_anchor or "").strip()
        if not anchor:
            return ""

        return anchor if anchor.startswith("#") else f"#{anchor.lstrip('#')}"
