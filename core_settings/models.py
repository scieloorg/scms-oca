from django.db import models
from wagtail.admin.edit_handlers import FieldPanel
from wagtail.images.edit_handlers import ImageChooserPanel
from wagtail.contrib.settings.models import BaseSetting, register_setting


@register_setting
class CustomSettings(BaseSetting):
    """
    This a settings model.

    More about look:
        https://docs.wagtail.org/en/stable/reference/contrib/settings.html
    """
    name = models.CharField(max_length=100, null=True, blank=True)

    favicon = models.ForeignKey(
        'wagtailimages.Image',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+'
    )

    admin_logo = models.ForeignKey(
        'wagtailimages.Image',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+'
    )

    panels = [
        FieldPanel('name'),
        ImageChooserPanel('favicon'),
        ImageChooserPanel('admin_logo'),
    ]
