from django.db import models
from django.utils.translation import gettext as _

from wagtail.admin.edit_handlers import FieldPanel
from wagtailautocomplete.edit_handlers import AutocompletePanel

from institution.models import Institution
from usefulmodels.models import Country, ThematicArea
from . import choices
from core.models import CommonControlField


class ScholarlyArticles(models.Model):
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

    def __unicode__(self):
        return self.doi if self.doi else ""

    def __str__(self):
        return self.doi if self.doi else ""

    class Meta:
        indexes = [
            models.Index(fields=['doi', ]),
            models.Index(fields=['title', ]),
            models.Index(fields=['volume', ]),
            models.Index(fields=['number', ]),
            models.Index(fields=['year', ]),
            models.Index(fields=['open_access_status', ]),
            models.Index(fields=['use_license', ]),
            models.Index(fields=['apc', ]),
            models.Index(fields=['journal', ]),
            models.Index(fields=['source', ]),
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
        AutocompletePanel('contributors'),
        AutocompletePanel('journal'),
        FieldPanel('source'),
    ]

    @property
    def data(self):
        d = {
            "article__doi": self.doi,
            "article__title": self.title,
            "article__volume": self.volume,
            "article__number": self.number,
            "article__year": self.year,
            "article__open_access_status": self.open_access_status,
            "article__use_license": self.use_license,
            "article__apc": self.apc,
            "article__contributors": [contributor.data for contributor in self.contributors.iterator()],
            "article__source": self.source
        }

        if self.journal:
            d.update(self.journal.data)

        return d


class Journals(models.Model):
    journal_issn_l = models.CharField(_("ISSN-L"), max_length=50, null=True, blank=True)
    journal_issns = models.CharField(_("ISSN's"), max_length=50, null=True, blank=True)
    journal_name = models.CharField(_("Journal Name"), max_length=255, null=True, blank=True)
    publisher = models.CharField(_("Publisher"), max_length=255, null=True, blank=True)
    journal_is_in_doaj = models.BooleanField(_("DOAJ"), default=False, null=True, blank=True)

    autocomplete_search_field = 'journal_name'

    def autocomplete_label(self):
        return self.journal_name

    def __unicode__(self):
        return self.journal_issn_l if self.journal_issn_l else ""

    def __str__(self):
        return self.journal_issn_l if self.journal_issn_l else ""

    class Meta:
        indexes = [
            models.Index(fields=['journal_issn_l', ]),
            models.Index(fields=['journal_issns', ]),
            models.Index(fields=['journal_name', ]),
            models.Index(fields=['publisher', ]),
            models.Index(fields=['journal_is_in_doaj', ]),
        ]

    panels = [
        FieldPanel('journal_issn_l'),
        FieldPanel('journal_issns'),
        FieldPanel('journal_name'),
        FieldPanel('publisher'),
        FieldPanel('journal_is_in_doaj'),
    ]

    @property
    def data(self):
        d = {
            "journal__issn_l": self.journal_issn_l,
            "journal__issns": self.journal_issns,
            "journal__name": self.journal_name,
            "journal__publisher": self.publisher,
            "journal__is_in_doaj": self.journal_is_in_doaj
        }
        return d


class Contributors(models.Model):
    family = models.CharField(_("Family Name"), max_length=255, null=True, blank=True)
    given = models.CharField(_("Given Name"), max_length=255, null=True, blank=True)
    orcid = models.CharField("ORCID", max_length=50, null=True, blank=True)
    authenticated_orcid = models.BooleanField(_("Authenticated"), default=False, null=True, blank=True)
    affiliation = models.ForeignKey('Affiliations', on_delete=models.SET_NULL, max_length=510, null=True, blank=True)

    autocomplete_search_field = 'given'

    def autocomplete_label(self):
        return self.given + self.family

    def __unicode__(self):
        return f"{self.family}, {self.given} ({self.orcid})"

    def __str__(self):
        return f"{self.family}, {self.given} ({self.orcid})"

    class Meta:
        indexes = [
            models.Index(fields=['family', ]),
            models.Index(fields=['given', ]),
            models.Index(fields=['orcid', ]),
            models.Index(fields=['authenticated_orcid', ]),
            models.Index(fields=['affiliation', ]),
        ]

    panels = [
        FieldPanel('family'),
        FieldPanel('given'),
        FieldPanel('orcid'),
        FieldPanel('authenticated_orcid'),
        AutocompletePanel('affiliation'),
    ]

    @property
    def data(self):
        d = {
            "contributor__family": self.family,
            "contributor__given": self.given,
            "contributor__orcid": self.orcid,
            "contributor__authenticated_orcid": self.authenticated_orcid
        }

        if self.affiliation:
            d.update(self.affiliation.data)

        return d


class Affiliations(models.Model):
    name = models.CharField(_("Affiliation Name"), max_length=510, null=True, blank=True)
    official = models.ForeignKey(Institution, verbose_name=_("Official Affiliation Name"), on_delete=models.SET_NULL,
                                 max_length=1020, null=True, blank=True)
    country = models.ForeignKey(Country, verbose_name=_("Country"), on_delete=models.SET_NULL,
                                 max_length=255, null=True, blank=True)

    autocomplete_search_field = 'name'

    def __unicode__(self):
        return self.name if self.name else ""

    def __str__(self):
        return self.name if self.name else ""

    def autocomplete_label(self):
        return str(self)

    class Meta:
        indexes = [
            models.Index(fields=['name', ]),
        ]

    panels = [
        FieldPanel('name'),
        AutocompletePanel('official'),
        AutocompletePanel('country'),
    ]

    @property
    def data(self):
        d = {
            "affiliation__name": self.name
        }

        if self.official:
            d.update(self.official.data)

        if self.country:
            d.update(self.country.data)

        return d


class RawUnpaywall(models.Model):
    doi = models.CharField(_("DOI"), max_length=100, null=False, blank=False)
    harvesting_creation = models.CharField(_("Harvesting date"), max_length=20, null=False, blank=False)
    is_paratext = models.BooleanField(_("Paratext"), default=False, null=True, blank=True)
    year = models.CharField(_("Year"), max_length=10, null=True, blank=True)
    # unpaywall genre
    resource_type = models.CharField(_("Resource Type"), max_length=50, choices=choices.TYPE_OF_RESOURCE, null=False,
                                     blank=True)
    update = models.CharField(_("Update"), max_length=20, null=True, blank=True)
    json = models.JSONField(_("JSON File"), null=True, blank=True)

    def __unicode__(self):
        return self.doi

    def __str__(self):
        return self.doi

    class Meta:
        indexes = [
            models.Index(fields=['doi', ]),
            models.Index(fields=['harvesting_creation', ]),
            models.Index(fields=['is_paratext', ]),
            models.Index(fields=['year', ]),
            models.Index(fields=['resource_type', ]),
            models.Index(fields=['update', ]),
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


class SupplementaryData(models.Model):
    doi = models.CharField(_("DOI"), max_length=100, null=False, blank=False)
    year = models.CharField(_("Year"), max_length=10, null=True, blank=True)
    json = models.JSONField(_("JSON File"), null=True, blank=True)

    def __unicode__(self):
        return self.doi

    def __str__(self):
        return self.doi

    class Meta:
        indexes = [
            models.Index(fields=['doi', ]),
            models.Index(fields=['year', ]),
        ]

    panels = [
        FieldPanel('doi'),
        FieldPanel('year'),
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
