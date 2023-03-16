from wagtail.fields import RichTextField
from wagtail.admin.panels import FieldPanel

from wagtail.models import Page


class FreePage(Page):
    body = RichTextField()

    content_panels = Page.content_panels + [
        FieldPanel("body", classname="full"),
    ]
