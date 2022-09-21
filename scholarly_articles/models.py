from django.db import models
from django.utils.translation import gettext as _

from wagtail.admin.edit_handlers import FieldPanel

from institution.models import Institution
from . import choices
from core.models import CommonControlField


class ScholarlyArticles(models.Model):
    doi = models.CharField(_("DOI"), max_length=255, null=True, blank=True)
    title = models.CharField(_("Title"), max_length=255, null=True, blank=True)
    volume = models.CharField(_("Volume"), max_length=255, null=True, blank=True)
    number = models.CharField(_("Number"), max_length=255, null=True, blank=True)
    year = models.CharField(_("Year"), max_length=4, null=True, blank=True)
    open_access_status = models.CharField(_("Open Access Status"), max_length=255, choices=choices.OA_STATUS,
                                     null=True,
                                     blank=True)
    use_license = models.CharField(_("Use License"), max_length=255, choices=choices.LICENSE, null=True, blank=True)
    apc = models.CharField(_("Article Processing Charge"), max_length=255, choices=choices.APC, null=True, blank=True)
    contributors = models.ManyToManyField("Contributors", verbose_name=_("Contributors"), blank=True)
    journal = models.ForeignKey("Journals", verbose_name=_("Journals"), on_delete=models.SET_NULL, max_length=255, null=True, blank=True)
    source = models.CharField(_("Record Source"), max_length=255, choices=choices.SOURCE, null=True, blank=True)

    def __unicode__(self):
        return self.doi

    def __str__(self):
        return self.doi

    class Meta:
        indexes = [
            models.Index(fields=['doi', ]),
        ]

    panels = [
        FieldPanel('doi'),
        FieldPanel('title'),
        FieldPanel('volume'),
        FieldPanel('number'),
        FieldPanel('year'),
        FieldPanel('open_access_status'),
        FieldPanel('use_license'),
        FieldPanel('apc'),
        FieldPanel('contributors'),
        FieldPanel('journal'),
        FieldPanel('source'),
    ]


class Journals(models.Model):
    journal_issn_l = models.CharField(_("ISSN-L"), max_length=255, null=True, blank=True)
    journal_issns = models.CharField(_("ISSN's"), max_length=255, null=True, blank=True)
    journal_name = models.CharField(_("Journal Name"), max_length=255, null=True, blank=True)
    publisher = models.CharField(_("Publisher"), max_length=255, null=True, blank=True)
    journal_is_in_doaj = models.BooleanField(_("DOAJ"), max_length=255, default=False, null=True, blank=True)

    def __unicode__(self):
        return self.journal_issn_l

    def __str__(self):
        return self.journal_issn_l

    class Meta:
        indexes = [
            models.Index(fields=['journal_issn_l', ]),
            models.Index(fields=['journal_issns', ]),
            models.Index(fields=['journal_name', ]),
        ]

    panels = [
        FieldPanel('journal_issn_l'),
        FieldPanel('journal_issns'),
        FieldPanel('journal_name'),
        FieldPanel('publisher'),
        FieldPanel('journal_is_in_doaj'),
    ]


class Contributors(models.Model):
    family = models.CharField(_("Family Name"), max_length=255, null=True, blank=True)
    given = models.CharField(_("Given Name"), max_length=255, null=True, blank=True)
    orcid = models.CharField("ORCID", max_length=255, null=True, blank=True)
    authenticated_orcid = models.BooleanField(_("Authenticated"), default=False, null=True, blank=True)
    affiliation = models.ForeignKey('Affiliations', on_delete=models.SET_NULL, max_length=510, null=True, blank=True)

    def __unicode__(self):
        return f"{self.family}, {self.given} ({self.orcid})"

    def __str__(self):
        return f"{self.family}, {self.given} ({self.orcid})"

    class Meta:
        indexes = [
            models.Index(fields=['family', ]),
            models.Index(fields=['given', ]),
            models.Index(fields=['orcid', ]),
            models.Index(fields=['affiliation', ]),
        ]

    panels = [
        FieldPanel('family'),
        FieldPanel('given'),
        FieldPanel('orcid'),
        FieldPanel('authenticated_orcid'),
        FieldPanel('affiliation'),
    ]


class Affiliations(models.Model):
    name = models.CharField(_("Affiliation Name"), max_length=510, null=True, blank=True)
    official = models.ForeignKey(Institution, verbose_name=_("Official Affiliation Name"), on_delete=models.SET_NULL, max_length=1020, null=True, blank=True)

    def __unicode__(self):
        return self.name

    def __str__(self):
        return self.name

    class Meta:
        indexes = [
            models.Index(fields=['name', ]),
        ]

    panels = [
        FieldPanel('name'),
        FieldPanel('official'),
    ]


class RawUnpaywall(models.Model):
    doi = models.CharField(_("DOI"), max_length=255, null=False, blank=False)
    harvesting_creation = models.CharField(_("Harvesting date"), max_length=255, null=False, blank=False)
    is_paratext = models.BooleanField(_("Paratext"), default=False, null=True, blank=True)
    year = models.CharField(_("Year"), max_length=255, null=True, blank=True)
    # unpaywall genre
    resource_type = models.CharField(_("Resource Type"), max_length=255, choices=choices.TYPE_OF_RESOURCE, null=False,
                                     blank=True)
    update = models.CharField(_("Update"), max_length=255, null=True, blank=True)
    json = models.JSONField(_("JSON File"), null=True, blank=True)

    def __unicode__(self):
        return self.doi

    def __str__(self):
        return self.doi

    class Meta:
        indexes = [
            models.Index(fields=['doi', ]),
            models.Index(fields=['year', ]),
            models.Index(fields=['resource_type', ]),
        ]

    panels = [
        FieldPanel('doi'),
        FieldPanel('harvesting_creation'),
        FieldPanel('is_paratext'),
        FieldPanel('year'),
        FieldPanel('resource_type'),
        FieldPanel('update'),
        FieldPanel('json'),
    ]


class ErrorLog(CommonControlField):
    error_type = models.CharField(_("Error Type"), max_length=50, null=True, blank=True, help_text=_("Type of python error."))
    error_message = models.CharField(_("Error Message"), max_length=255, null=True, blank=True, help_text=_("Message of python error."))
    error_description = models.TextField(_("Error description"), max_length=255,
                                         null=True, blank=True, help_text=_("More context about the error"))

    data_reference = models.CharField(_("Reference data"), max_length=10, null=True,
                                      blank=True, help_text=_("Reference to the data, can be id, line. Use line:10 or id:452 to to differ between id|line."))
    data = models.TextField(_("Data"), max_length=10, null=True, blank=True, help_text=_("Data when the error happened."))
    data_type = models.CharField(_("Data type"), max_length=255, null=True,
                                 blank=True, help_text=_("Data type, can the the model, ex.: models.RawUnpaywall"))
