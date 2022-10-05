import os

from django.db import models
from django.utils.translation import gettext as _
from wagtail.admin.edit_handlers import FieldPanel, HelpPanel
from wagtail.documents.edit_handlers import DocumentChooserPanel

from core.models import CommonControlField
from core_oca.models import CommonFields

from .forms import PolicyDirectoryFileForm, PolicyDirectoryForm
from institution.models import Institution
from . import choices


class PolicyDirectory(CommonFields):
    class Meta:
        verbose_name_plural = _('Policy Directory')

    institutions = models.ManyToManyField(Institution, verbose_name=_("Institution"), blank=True)

    classification = models.CharField(_("Classification"), choices=choices.classification,
                                      max_length=255, null=True, blank=True)

    date = models.DateField(_("Date"), max_length=255, null=True, blank=True)


    panels = [
        HelpPanel('Documentos de promoção, posicionamentos ou mandatos sobre Ciência Aberta elaborados e publicados por instituições brasileiras, tais como: universidades, sociedades científicas, institutos de pesquisa e agências de fomento.'),
        FieldPanel('title'),
        FieldPanel('link'),
        FieldPanel('description'),
        FieldPanel('date'),
        FieldPanel('institutions'),

        FieldPanel('thematic_areas'),
        FieldPanel('keywords'),
        FieldPanel('classification'),
        FieldPanel('practice'),

        FieldPanel('source'),
        FieldPanel('record_status'),

    ]

    def __unicode__(self):
        return u'%s' % self.title

    def __str__(self):
        return u'%s' % self.title
    base_form_class = PolicyDirectoryForm

class PolicyDirectoryFile(CommonControlField):
    class Meta:
        verbose_name_plural = _('Policy Directory Upload')

    attachment = models.ForeignKey(
        'wagtaildocs.Document',
        verbose_name=_("Attachement"),
        null=True, blank=False,
        on_delete=models.SET_NULL,
        related_name='+'
    )
    is_valid = models.BooleanField(_("Is valid?"), default=False, blank=True,
                                   null=True)
    line_count = models.IntegerField(_("Number of lines"), default=0,
                                     blank=True, null=True)

    def filename(self):
        return os.path.basename(self.attachment.name)

    panels = [
        DocumentChooserPanel('attachment')
    ]
    base_form_class = PolicyDirectoryFileForm
