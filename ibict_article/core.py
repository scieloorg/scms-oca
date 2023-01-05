from django.db import models
from django.utils.translation import gettext as _

from wagtail.admin.edit_handlers import FieldPanel
from wagtailautocomplete.edit_handlers import AutocompletePanel

from core.models import CommonControlField
from core.forms import CoreAdminModelForm

from .choices import TYPES
from usefulmodels.models import City, State, Country


class GenericField(models.Model):
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
            'generic_field__text': self.text,
        }

    @classmethod
    def get_or_create(cls, text):

        try:
            generic_fields = cls.objects.filter(text=text)
            generic_field = generic_fields[0]
        except IndexError:
            generic_field = GenericField()
            generic_field.text = text
            generic_field.save()

        return generic_field

    base_form_class = CoreAdminModelForm


