from django.db import models
from django.db.models import Count, Q
from django.utils.translation import gettext as _
from wagtail.admin.panels import FieldPanel
from wagtailautocomplete.edit_handlers import AutocompletePanel

from institution.models import Institution
from usefulmodels.models import Country, State, ThematicArea
from . import choices
from core.models import CommonControlField


class ScholarlyArticles(models.Model):
    doi = models.CharField(_("DOI"), max_length=100, null=True, blank=True)
    title = models.CharField(_("Title"), max_length=510, null=True, blank=True)
    volume = models.CharField(_("Volume"), max_length=20, null=True, blank=True)
    number = models.CharField(_("Number"), max_length=20, null=True, blank=True)
    year = models.CharField(_("Year"), max_length=20, null=True, blank=True)
    open_access_status = models.CharField(
        _("Open Access Status"),
        max_length=50,
        choices=choices.OA_STATUS,
        null=True,
        blank=True,
    )
    use_license = models.CharField(
        _("Use License"), max_length=50, choices=choices.LICENSE, null=True, blank=True
    )
    license = models.ForeignKey(
        "License",
        verbose_name=_("License"),
        on_delete=models.SET_NULL,
        max_length=255,
        null=True,
        blank=True,
    )
    apc = models.CharField(
        _("Article Processing Charge"),
        max_length=20,
        choices=choices.APC,
        null=True,
        blank=True,
    )
    contributors = models.ManyToManyField(
        "Contributors", verbose_name=_("Contributors"), blank=True
    )
    journal = models.ForeignKey(
        "Journals",
        verbose_name=_("Journals"),
        on_delete=models.SET_NULL,
        max_length=255,
        null=True,
        blank=True,
    )
    source = models.CharField(
        _("Record Source"), max_length=50, choices=choices.SOURCE, null=True, blank=True
    )

    def __unicode__(self):
        return self.doi if self.doi else ""

    def __str__(self):
        return self.doi if self.doi else ""

    class Meta:
        indexes = [
            models.Index(
                fields=[
                    "doi",
                ]
            ),
            models.Index(
                fields=[
                    "title",
                ]
            ),
            models.Index(
                fields=[
                    "volume",
                ]
            ),
            models.Index(
                fields=[
                    "number",
                ]
            ),
            models.Index(
                fields=[
                    "year",
                ]
            ),
            models.Index(
                fields=[
                    "open_access_status",
                ]
            ),
            models.Index(
                fields=[
                    "use_license",
                ]
            ),
            models.Index(
                fields=[
                    "apc",
                ]
            ),
            models.Index(
                fields=[
                    "journal",
                ]
            ),
            models.Index(
                fields=[
                    "source",
                ]
            ),
        ]

    panels = [
        FieldPanel("doi"),
        FieldPanel("title"),
        FieldPanel("volume"),
        FieldPanel("number"),
        FieldPanel("year"),
        FieldPanel("open_access_status"),
        FieldPanel("use_license"),
        FieldPanel("license"),
        FieldPanel("apc"),
        AutocompletePanel("contributors"),
        AutocompletePanel("journal"),
        FieldPanel("source"),
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
            "article__contributors": [
                contributor.data for contributor in self.contributors.iterator()
            ],
            "article__source": self.source,
        }

        if self.journal:
            d.update(self.journal.data)

        return d

    @classmethod
    def filter_items_to_generate_indicators(
        cls,
        begin_year,
        end_year,
        institution__name=None,
        thematic_area__level0=None,
        thematic_area__level1=None,
        location__state__code=None,
        location__state__region=None,
    ):
        params = dict(
            open_access_status__isnull=False,
            use_license__isnull=False,
            year__gte=begin_year,
            year__lte=end_year,
            contributors__affiliation__official__name=institution__name,
            contributors__affiliation__official__location__state__acronym=location__state__code,
            contributors__affiliation__official__location__state__region=location__state__region,
            contributors__thematic_areas__level0=thematic_area__level0,
            contributors__thematic_areas__level1=thematic_area__level1,
        )
        params = {k: v for k, v in params.items() if v}
        return cls.objects.filter(**params)

    @classmethod
    def parameters_for_values(
        cls,
        by_open_access_status=False,
        by_use_license=False,
        by_institution=False,
        by_thematic_area_level0=False,
        by_thematic_area_level1=False,
        by_state=False,
        by_region=False,
    ):
        selected_attributes = ["year"]
        if by_open_access_status:
            selected_attributes += ["open_access_status"]
        if by_use_license:
            selected_attributes += ["use_license"]
        if by_institution:
            selected_attributes += Institution.parameters_for_values("contributors__affiliation__official")
        if by_state or by_region:
            selected_attributes += State.parameters_for_values(
                "contributors__affiliation__official__location__state", by_state, by_state, by_region
            )
        if by_thematic_area_level0 or by_thematic_area_level1:
            selected_attributes += ThematicArea.parameters_for_values(
                "contributors__thematic_areas", by_thematic_area_level0, by_thematic_area_level1
            )
        return selected_attributes

    @classmethod
    def group(
        cls,
        query_result,
        selected_attributes,
        order_by="year",
    ):
        for item in (
            query_result.values(*selected_attributes)
            .annotate(count=Count("id"))
            .order_by(order_by)
            .iterator()
        ):
            d = {}
            for k, v in item.items():
                k = k.replace("contributors__affiliation__official__location__", "")
                k = k.replace("contributors__affiliation__official__name", "institution__name")
                k = k.replace("thematic_areas__", "thematic_area__")

                d[k] = v
            yield d


class Journals(models.Model):
    journal_issn_l = models.CharField(_("ISSN-L"), max_length=50, null=True, blank=True)
    journal_issns = models.CharField(_("ISSN's"), max_length=50, null=True, blank=True)
    journal_name = models.CharField(
        _("Journal Name"), max_length=255, null=True, blank=True
    )
    publisher = models.CharField(_("Publisher"), max_length=255, null=True, blank=True)
    journal_is_in_doaj = models.BooleanField(
        _("DOAJ"), default=False, null=True, blank=True
    )

    autocomplete_search_field = "journal_name"

    def autocomplete_label(self):
        return self.journal_name

    def __unicode__(self):
        return self.journal_issn_l if self.journal_issn_l else ""

    def __str__(self):
        return self.journal_issn_l if self.journal_issn_l else ""

    class Meta:
        indexes = [
            models.Index(
                fields=[
                    "journal_issn_l",
                ]
            ),
            models.Index(
                fields=[
                    "journal_issns",
                ]
            ),
            models.Index(
                fields=[
                    "journal_name",
                ]
            ),
            models.Index(
                fields=[
                    "publisher",
                ]
            ),
            models.Index(
                fields=[
                    "journal_is_in_doaj",
                ]
            ),
        ]

    panels = [
        FieldPanel("journal_issn_l"),
        FieldPanel("journal_issns"),
        FieldPanel("journal_name"),
        FieldPanel("publisher"),
        FieldPanel("journal_is_in_doaj"),
    ]

    @property
    def data(self):
        d = {
            "journal__issn_l": self.journal_issn_l,
            "journal__issns": self.journal_issns,
            "journal__name": self.journal_name,
            "journal__publisher": self.publisher,
            "journal__is_in_doaj": self.journal_is_in_doaj,
        }
        return d


class Contributors(models.Model):
    family = models.CharField(_("Family Name"), max_length=255, null=True, blank=True)
    given = models.CharField(_("Given Name"), max_length=255, null=True, blank=True)
    orcid = models.CharField("ORCID", max_length=50, null=True, blank=True)
    authenticated_orcid = models.BooleanField(
        _("Authenticated"), default=False, null=True, blank=True
    )
    affiliation = models.ForeignKey(
        "Affiliations", on_delete=models.SET_NULL, max_length=510, null=True, blank=True
    )

    autocomplete_search_field = "given"

    def autocomplete_label(self):
        return "%s %s" % (self.given, self.family)

    def __unicode__(self):
        return f"{self.family}, {self.given} ({self.orcid})"

    def __str__(self):
        return f"{self.family}, {self.given} ({self.orcid})"

    class Meta:
        indexes = [
            models.Index(
                fields=[
                    "family",
                ]
            ),
            models.Index(
                fields=[
                    "given",
                ]
            ),
            models.Index(
                fields=[
                    "orcid",
                ]
            ),
            models.Index(
                fields=[
                    "authenticated_orcid",
                ]
            ),
            models.Index(
                fields=[
                    "affiliation",
                ]
            ),
        ]

    panels = [
        FieldPanel("family"),
        FieldPanel("given"),
        FieldPanel("orcid"),
        FieldPanel("authenticated_orcid"),
        AutocompletePanel("affiliation"),
    ]

    @property
    def data(self):
        d = {
            "contributor__family": self.family,
            "contributor__given": self.given,
            "contributor__orcid": self.orcid,
            "contributor__authenticated_orcid": self.authenticated_orcid,
        }

        if self.affiliation:
            d.update(self.affiliation.data)

        return d


class Affiliations(models.Model):
    name = models.CharField(
        _("Affiliation Name"), max_length=510, null=True, blank=True
    )
    official = models.ForeignKey(
        Institution,
        verbose_name=_("Official Affiliation Name"),
        on_delete=models.SET_NULL,
        max_length=1020,
        null=True,
        blank=True,
    )
    country = models.ForeignKey(
        Country,
        verbose_name=_("Country"),
        on_delete=models.SET_NULL,
        max_length=255,
        null=True,
        blank=True,
    )

    autocomplete_search_field = "name"

    def __unicode__(self):
        return self.name if self.name else ""

    def __str__(self):
        return self.name if self.name else ""

    def autocomplete_label(self):
        return str(self)

    class Meta:
        indexes = [
            models.Index(
                fields=[
                    "name",
                ]
            ),
            models.Index(
                fields=[
                    "country",
                ]
            ),
            models.Index(
                fields=[
                    "official",
                ]
            ),
        ]

    panels = [
        FieldPanel("name"),
        AutocompletePanel("official"),
        AutocompletePanel("country"),
    ]

    @property
    def data(self):
        d = {"affiliation__name": self.name}

        if self.official:
            d.update(self.official.data)

        if self.country:
            d.update(self.country.data)

        return d


class RawUnpaywall(models.Model):
    doi = models.CharField(_("DOI"), max_length=100, null=False, blank=False)
    harvesting_creation = models.CharField(
        _("Harvesting date"), max_length=20, null=False, blank=False
    )
    is_paratext = models.BooleanField(
        _("Paratext"), default=False, null=True, blank=True
    )
    year = models.CharField(_("Year"), max_length=10, null=True, blank=True)
    # unpaywall genre
    resource_type = models.CharField(
        _("Resource Type"),
        max_length=50,
        choices=choices.TYPE_OF_RESOURCE,
        null=False,
        blank=True,
    )
    update = models.CharField(_("Update"), max_length=20, null=True, blank=True)
    json = models.JSONField(_("JSON File"), null=True, blank=True)

    def __unicode__(self):
        return self.doi

    def __str__(self):
        return self.doi

    class Meta:
        indexes = [
            models.Index(
                fields=[
                    "doi",
                ]
            ),
            models.Index(
                fields=[
                    "harvesting_creation",
                ]
            ),
            models.Index(
                fields=[
                    "is_paratext",
                ]
            ),
            models.Index(
                fields=[
                    "year",
                ]
            ),
            models.Index(
                fields=[
                    "resource_type",
                ]
            ),
            models.Index(
                fields=[
                    "update",
                ]
            ),
        ]

    panels = [
        FieldPanel("doi"),
        FieldPanel("harvesting_creation"),
        FieldPanel("is_paratext"),
        FieldPanel("year"),
        FieldPanel("resource_type"),
        FieldPanel("update"),
        FieldPanel("json"),
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
            models.Index(
                fields=[
                    "doi",
                ]
            ),
            models.Index(
                fields=[
                    "year",
                ]
            ),
        ]

    panels = [
        FieldPanel("doi"),
        FieldPanel("year"),
        FieldPanel("json"),
    ]


class ErrorLog(CommonControlField):
    error_type = models.CharField(
        _("Error Type"),
        max_length=50,
        null=True,
        blank=True,
        help_text=_("Type of python error."),
    )
    error_message = models.CharField(
        _("Error Message"),
        max_length=255,
        null=True,
        blank=True,
        help_text=_("Message of python error."),
    )
    error_description = models.TextField(
        _("Error description"),
        max_length=255,
        null=True,
        blank=True,
        help_text=_("More context about the error"),
    )

    data_reference = models.CharField(
        _("Reference data"),
        max_length=10,
        null=True,
        blank=True,
        help_text=_(
            "Reference to the data, can be id, line. Use line:10 or id:452 to to differ between id|line."
        ),
    )
    data = models.TextField(
        _("Data"),
        max_length=10,
        null=True,
        blank=True,
        help_text=_("Data when the error happened."),
    )
    data_type = models.CharField(
        _("Data type"),
        max_length=255,
        null=True,
        blank=True,
        help_text=_("Data type, can the the model, ex.: models.RawUnpaywall"),
    )


class License(models.Model):
    """
    A class to represent a license designed in the SciELO context.

    Attributes
    ----------
    name: The name of license, it is not required
    delay_in_days:
        Number of days between the publication date of the work and the start date of this license
    start: Date on which this license begins to take effect
    URL: Link to a web page describing this license

    Methods
    -------
    TODO
    """

    name = models.CharField(
        _("Name"),
        max_length=100,
        null=True,
        blank=True,
        help_text=_("The name of license, it is not required"),
    )
    delay_in_days = models.IntegerField(
        _("Delay in Days"),
        null=True,
        blank=True,
        help_text=_(
            "Number of days between the publication date of the work and the start date of this license"
        ),
    )
    start = models.CharField(
        _("Stard Date"),
        max_length=100,
        null=True,
        blank=True,
        help_text=_("Date on which this license begins to take effect"),
    )
    url = models.URLField(
        _("URL"), help_text="Link to a web page describing this license"
    )

    def __unicode__(self):
        return self.name or self.url

    def __str__(self):
        return self.name or self.url
