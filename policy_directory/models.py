import os

from django.db import models
from django.utils.translation import gettext as _
from taggit.managers import TaggableManager
from wagtail.admin.edit_handlers import FieldPanel, HelpPanel
from wagtail.documents.edit_handlers import DocumentChooserPanel

from core.models import CommonControlField
from institution.models import Institution
from usefulmodels.models import ThematicArea, Pratice, Action

from .forms import PolicyDirectoryFileForm, PolicyDirectoryForm

from . import choices
class PolicyDirectory(CommonControlField):
    class Meta:
        verbose_name_plural = _('Policy Directory')

    title = models.CharField(_("Title"), max_length=255, null=False, blank=False)
    link = models.URLField(_("Link"), null=False, blank=False)
    description = models.TextField(_("Description"), max_length=255,
                                   null=True, blank=True)
    date = models.DateField(_("Start Date"), max_length=255,
                                  null=True, blank=True)

    institutions = models.ManyToManyField(Institution, verbose_name=_("Institution"), blank=True)
    thematic_areas = models.ManyToManyField(ThematicArea, verbose_name=_("Thematic Area"), blank=True)

    pratice = models.ForeignKey(Pratice, verbose_name=_("Pratice"),
                                null=True, blank=True, on_delete=models.SET_NULL)
    action = models.ForeignKey(Action, verbose_name=_("Action"), null=True, blank=True, on_delete=models.SET_NULL)

    classification = models.CharField(_("Classification"), choices=choices.classification,
                                      max_length=255, null=True, blank=True)

    keywords = TaggableManager(_("Keywords"), blank=True)

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
        FieldPanel('pratice'),
        FieldPanel('action'),
    ]
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
