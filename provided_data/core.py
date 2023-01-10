from django.db import models
from django.utils.translation import gettext as _

from wagtail.admin.edit_handlers import FieldPanel
from wagtailautocomplete.edit_handlers import AutocompletePanel
from taggit.managers import TaggableManager

from core.models import CommonControlField
from core.forms import CoreAdminModelForm

from .choices import TYPES
from usefulmodels.models import City, State, Country


class CommonTextField(models.Model):
    text = models.CharField(_("Text"), max_length=510, null=True, blank=True)

    autocomplete_search_field = 'text'

    def autocomplete_label(self):
        return self.text

    def __unicode__(self):
        return f'{self.text}'

    def __str__(self):
        return f'{self.text}'

    class Meta:
        indexes = [
            models.Index(fields=['text', ]),
        ]

    panels = [
        FieldPanel('text'),
    ]

    @property
    def data(self):
        return {
            'common_text_field__text': self.text,
        }

    @classmethod
    def create(cls, text):

        common_text_field = CommonTextField()
        common_text_field.text = text
        common_text_field.save()

        return common_text_field

    base_form_class = CoreAdminModelForm
