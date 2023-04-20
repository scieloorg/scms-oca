from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import models
from django.utils.translation import gettext as _
from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel
from wagtail.admin.panels import FieldPanel, InlinePanel, ObjectList, TabbedInterface
from wagtail.contrib.settings.models import BaseSiteSetting, register_setting
from wagtail.fields import RichTextField
from wagtail.models import Orderable

from . import choices

User = get_user_model()


@register_setting
class CustomSettings(BaseSiteSetting, ClusterableModel):
    """
    This a settings model.

    More about look:
        https://docs.wagtail.org/en/stable/reference/contrib/settings.html
    """

    class Meta:
        verbose_name = _("Configuração do site")
        verbose_name_plural = _("Configuração do site")

    name = models.CharField(max_length=100, null=True, blank=True)
    email = models.EmailField(max_length=100, null=True, blank=True)
    phone = models.CharField(max_length=100, null=True, blank=True)

    footer_text = RichTextField(null=True, blank=True)

    favicon = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    admin_logo = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    site_logo = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    site_panels = [
        FieldPanel("name"),
        FieldPanel("email"),
        FieldPanel("phone"),
        FieldPanel("footer_text", classname="full"),
        FieldPanel("favicon"),
        FieldPanel("site_logo"),
    ]

    admin_panels = [
        FieldPanel("admin_logo"),
    ]

    panels_moderation = [
        InlinePanel("moderation", label=_("Moderation"), classname="collapsed"),
    ]

    edit_handler = TabbedInterface(
        [
            ObjectList(site_panels, heading=_("Site settings")),
            ObjectList(admin_panels, heading=_("Admin settings")),
            ObjectList(panels_moderation, heading=_("Moderation")),
        ]
    )


class Moderation(Orderable):
    """
    A class to represent a moderation configuration to specific models.

    Attributes
    ----------
    custom_setting = the foreign key to Custom Settings
    title = the title of the moderation
    moderator = the moderator can be a specific user
    group_moderator = the group moderator can be a group of user
    send_mail = must send e-mail 

    Methods
    -------
    TODO
    """

    custom_setting = ParentalKey(
        CustomSettings, on_delete=models.CASCADE, related_name="moderation"
    )

    title = models.CharField(_("Title"), max_length=256, null=True, blank=True)

    model = models.CharField(
        _("Model"),
        choices=choices.models,
        max_length=255,
        null=True,
        blank=True,
        help_text="Indicate which model should be moderated"
    )

    moderator = models.ForeignKey(
        User,
        verbose_name=_("Moderator"),
        related_name="%(class)s_moderator",
        editable=True,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    group_moderator = models.ForeignKey(
        Group,
        verbose_name=_("Grupo Moderator"),
        related_name="%(class)s_group_moderator",
        editable=True,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    send_mail = models.BooleanField(
        default=True, verbose_name=_("Send e-mail to moderator(s)"), help_text="This field indicate if any record is create if must send e-mail to moderator or a group of moderators"
    )

    class Meta:
        verbose_name = _("Moderation")
        verbose_name_plural = _("Moderations")

    def __unicode__(self):
        return "%s" % self.title or ""

    def __str__(self):
        return "%s" % self.title or ""
