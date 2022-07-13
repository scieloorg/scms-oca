from django.db import models
from django.utils.translation import gettext as _

from wagtail.admin.edit_handlers import FieldPanel

from . import choices


class ScholarlyArticles(models.Model):
    doi = models.CharField(_("DOI"), max_length=255, null=False, blank=False)
    doi_url = models.URLField(_("DOI URL"), max_length=255, null=True, blank=True)
    # unpaywall genre
    resource_type = models.CharField(_("Resource Type"), max_length=255, choices=choices.TYPE_OF_RESOURCE, null=False,
                                     blank=True)
    is_oa = models.BooleanField(_("Opens Access"), max_length=255, null=True, blank=True)
    journal_is_in_doaj = models.BooleanField(_("DOAJ"), max_length=255, null=True, blank=True)
    journal_issns = models.CharField(_("ISSN's"), max_length=255, null=False, blank=False)
    journal_issn_l = models.CharField(_("ISSN-L"), max_length=255, null=False, blank=False)
    journal_name = models.CharField(_("Journal Name"), max_length=255, null=True, blank=True)
    oa_status = models.CharField(_("OA Status"), max_length=20, choices=choices.OA_STATUS, null=True, blank=True)
    published_date = models.DateTimeField(_("Published Date"), max_length=20, null=True, blank=True)
    publisher = models.CharField(_("Publisher"), max_length=255, null=True, blank=True)
    title = models.CharField(_("Title"), max_length=255, null=True, blank=True)
    update = models.DateTimeField(_("Update"), max_length=20, null=True, blank=True)
    year = models.IntegerField(_("Year"), null=True, blank=True)
    article_json = models.JSONField(_("JSON File"), null=True, blank=True)
    contributors = models.ManyToManyField(_("Contributors"))

    def __unicode__(self):
        return self.doi

    def __str__(self):
        return self.doi

    panels = [
        FieldPanel('doi'),
        FieldPanel('doi_url'),
        FieldPanel('resource_type'),
        FieldPanel('is_oa'),
        FieldPanel('journal_is_in_doaj'),
        FieldPanel('journal_issns'),
        FieldPanel('journal_issn_l'),
        FieldPanel('journal_name'),
        FieldPanel('oa_status'),
        FieldPanel('published_date'),
        FieldPanel('publisher'),
        FieldPanel('title'),
        FieldPanel('update'),
        FieldPanel('year'),
        FieldPanel('article_json'),
        FieldPanel('contributors'),
    ]


class Contributors(models.Model):
    family = models.CharField(_("Family Name"), max_length=255, null=False, blank=False)
    given = models.CharField(_("Given Name"), max_length=255, null=False, blank=False)
    orcid = models.CharField("ORCID", max_length=255, null=False, blank=False)
    authenticated_orcid = models.BooleanField(_("Authenticated"), max_length=20, null=False, blank=False)
    affiliation = models.ForeignKey(_("Affiliations"), on_delete=models.CASCADE)

    def __unicode__(self):
        return self.orcid

    def __str__(self):
        return self.orcid

    panels = [
        FieldPanel('family'),
        FieldPanel('given'),
        FieldPanel('orcid'),
        FieldPanel('authenticated_orcid'),
        FieldPanel('affiliation'),
    ]


class Affiliations(models.Model):
    institution_name = models.CharField(_("Institution Name"), max_length=100, null=False, blank=False)
    institution_acronym = models.CharField(_("Institution Acronym"), max_length=10, null=True, blank=True)
    institution_place = models.CharField(_("Institution Place"), max_length=255, null=True, blank=True)
    institution_department = models.CharField(_("Institution Department"), max_length=255, null=True, blank=True)

    def __unicode__(self):
        return self.institution_name

    def __str__(self):
        return self.institution_name

    panels = [
        FieldPanel('institution_name'),
        FieldPanel('institution_acronym'),
        FieldPanel('institution_place'),
        FieldPanel('institution_department'),
    ]
