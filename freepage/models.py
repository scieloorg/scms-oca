from django.db import models
from wagtail.admin.panels import FieldPanel
from wagtail.fields import RichTextField
from wagtail.models import Page


class FreePage(Page):
    body = RichTextField()

    embed = models.TextField(
        "Embed",
        null=True,
        blank=True,
        help_text="Embed content for the page, such as an iframe or other embed code.",
    )
    use_only_embed = models.BooleanField(
        default=False,
        verbose_name="Set only embed",
        help_text="If checked, the page will only display the embed content without the body text.",
    )

    content_panels = Page.content_panels + [
        FieldPanel("body", classname="full"),
        FieldPanel("embed", classname="full"),
        FieldPanel("use_only_embed", classname="full"),
    ]
