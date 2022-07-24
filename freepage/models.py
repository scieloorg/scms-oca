from wagtail.core.fields import RichTextField
from wagtail.admin.edit_handlers import FieldPanel

from wagtail.core.models import Page

class FreePage(Page):
    body = RichTextField()

    content_panels = Page.content_panels + [
        FieldPanel('body', classname="full"),
    ]