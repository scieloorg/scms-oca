from django.db import models
from django.utils.translation import gettext as _

from wagtail.admin.edit_handlers import FieldPanel

from . import choices
from core.models import CommonControlField


class ScholarlyArticles(models.Model):
    doi = models.CharField(_("DOI"), max_length=255, null=True, blank=True)
    year = models.CharField(_("Year"), max_length=4, null=True, blank=True)
    contributors = models.ManyToManyField(_("Contributors"), null=True, blank=True)
    journal = models.ForeignKey('Journals', on_delete=models.SET_NULL, max_length=255, null=True, blank=True)

    def __unicode__(self):
        return self.doi

    def __str__(self):
        return self.doi

    panels = [
        FieldPanel('doi'),
        FieldPanel('year'),
        FieldPanel('contributors'),
        FieldPanel('journal'),
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
    affiliation = models.ForeignKey(_("Affiliations"), on_delete=models.SET_NULL, max_length=255, null=True, blank=True)

    def __unicode__(self):
        return f"{self.family}, {self.given} ({self.orcid})"

    def __str__(self):
        return f"{self.family}, {self.given} ({self.orcid})"

    panels = [
        FieldPanel('family'),
        FieldPanel('given'),
        FieldPanel('orcid'),
        FieldPanel('authenticated_orcid'),
        FieldPanel('affiliation'),
    ]


class Affiliations(models.Model):
    name = models.CharField(_("Affiliation Name"), max_length=255, null=True, blank=True)

    def __unicode__(self):
        return self.name

    def __str__(self):
        return self.name

    panels = [
        FieldPanel('name'),
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

    panels = [
        FieldPanel('doi'),
        FieldPanel('harvesting_creation'),
        FieldPanel('is_paratext'),
        FieldPanel('year'),
        FieldPanel('resource_type'),
        FieldPanel('update'),
        FieldPanel('json'),
    ]
