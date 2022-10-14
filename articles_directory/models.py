from django.db import models
from django.utils.translation import gettext as _

from wagtail.admin.edit_handlers import FieldPanel

from institution.models import Institution
from . import choices
from core.models import CommonControlField
from usefulmodels.models import Practice, ThematicArea, Action


class Articles(models.Model):
    doi = models.CharField(_("DOI"), max_length=100, null=True, blank=True)
    title = models.CharField(_("Title"), max_length=510, null=True, blank=True)
    volume = models.CharField(_("Volume"), max_length=20, null=True, blank=True)
    number = models.CharField(_("Number"), max_length=20, null=True, blank=True)
    year = models.CharField(_("Year"), max_length=20, null=True, blank=True)
    open_access_status = models.CharField(_("Open Access Status"), max_length=50, choices=choices.OA_STATUS,
                                     null=True,
                                     blank=True)
    use_license = models.CharField(_("Use License"), max_length=50, choices=choices.LICENSE, null=True, blank=True)
    apc = models.CharField(_("Article Processing Charge"), max_length=20, choices=choices.APC, null=True, blank=True)
    contributors = models.ManyToManyField("Contributors", verbose_name=_("Contributors"), blank=True)
    journal = models.ForeignKey("Journals", verbose_name=_("Journals"), on_delete=models.SET_NULL, max_length=255, null=True, blank=True)
    source = models.CharField(_("Record Source"), max_length=50, choices=choices.SOURCE, null=True, blank=True)

    thematic_areas = models.ManyToManyField(ThematicArea, verbose_name=_("Thematic Area"), blank=True)
    practice = models.ForeignKey(Practice, verbose_name=_("Practice"),
                                 null=True, blank=True, on_delete=models.SET_NULL)
    action = models.ForeignKey(Action, verbose_name=_("Action"), null=True, blank=True, on_delete=models.SET_NULL)

    def __unicode__(self):
        return self.doi

    def __str__(self):
        return self.doi

    class Meta:
        indexes = [
            models.Index(fields=['doi', ]),
        ]

    # panels = [
    #     FieldPanel('doi'),
    #     FieldPanel('title'),
    #     FieldPanel('volume'),
    #     FieldPanel('number'),
    #     FieldPanel('year'),
    #     FieldPanel('open_access_status'),
    #     FieldPanel('use_license'),
    #     FieldPanel('apc'),
    #     FieldPanel('contributors'),
    #     FieldPanel('journal'),
    #     FieldPanel('source'),
    # ]


class Journals(models.Model):
    journal_issn_l = models.CharField(_("ISSN-L"), max_length=50, null=True, blank=True)
    journal_issns = models.CharField(_("ISSN's"), max_length=50, null=True, blank=True)
    journal_name = models.CharField(_("Journal Name"), max_length=255, null=True, blank=True)
    publisher = models.CharField(_("Publisher"), max_length=255, null=True, blank=True)
    journal_is_in_doaj = models.BooleanField(_("DOAJ"), default=False, null=True, blank=True)

    def __unicode__(self):
        return self.journal_issn_l

    def __str__(self):
        return self.journal_issn_l

    class Meta:
        indexes = [
            models.Index(fields=['journal_issn_l', ]),
        ]

    # panels = [
    #     FieldPanel('journal_issn_l'),
    #     FieldPanel('journal_issns'),
    #     FieldPanel('journal_name'),
    #     FieldPanel('publisher'),
    #     FieldPanel('journal_is_in_doaj'),
    # ]


class Contributors(models.Model):
    family = models.CharField(_("Family Name"), max_length=255, null=True, blank=True)
    given = models.CharField(_("Given Name"), max_length=255, null=True, blank=True)
    orcid = models.CharField("ORCID", max_length=50, null=True, blank=True)
    authenticated_orcid = models.BooleanField(_("Authenticated"), default=False, null=True, blank=True)
    affiliation = models.ManyToManyField('Affiliations', blank=True)

    def __unicode__(self):
        return f"{self.family}, {self.given} ({self.orcid})"

    def __str__(self):
        return f"{self.family}, {self.given} ({self.orcid})"

    class Meta:
        indexes = [
            models.Index(fields=['orcid', ]),
        ]

    # panels = [
    #     FieldPanel('family'),
    #     FieldPanel('given'),
    #     FieldPanel('orcid'),
    #     FieldPanel('authenticated_orcid'),
    #     FieldPanel('affiliation'),
    # ]


class Affiliations(models.Model):
    name = models.CharField(_("Declared Name"), max_length=510, null=True, blank=True)
    official = models.ForeignKey(Institution, verbose_name=_("Official Affiliation Name"), on_delete=models.SET_NULL,
                                 related_name="official_name", max_length=1020, null=True, blank=True)
    source = models.CharField(_("Source"), max_length=510, null=True, blank=True)

    def __unicode__(self):
        return self.name or ""

    def __str__(self):
        return self.name or ""

    panels = [
        FieldPanel('name'),
        FieldPanel('official'),
        FieldPanel('source'),
    ]
