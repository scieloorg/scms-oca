from django.db import models
from django.utils.translation import gettext as _

from wagtail.admin.panels import FieldPanel
from wagtailautocomplete.edit_handlers import AutocompletePanel

from institution.models import Institution
from usefulmodels.models import Country
from . import choices
from core.models import CommonControlField


class ScholarlyArticles(models.Model):
    doi = models.CharField(_("DOI"), max_length=100, null=True, blank=True)
    id_int_production = models.CharField(
        _("Id Intellectual Production"), max_length=100, null=True, blank=True
    )
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
        null=True,
        blank=True,
    )
    source = models.CharField(
        _("Record Source"), max_length=50, choices=choices.SOURCE, null=True, blank=True
    )

    def __unicode__(self):
        return str("%s") % self.doi or self.id_int_production

    def __str__(self):
        return str("%s") % self.doi or self.id_int_production

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
        FieldPanel("id_int_production"),
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
            "article__id_int_production": self.id_int_production,
            "article__title": self.title,
            "article__volume": self.volume,
            "article__number": self.number,
            "article__year": self.year,
            "article__open_access_status": self.open_access_status,
            "article__use_license": self.use_license,
            "article__license": self.license.name if self.license else "",
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
    def get_or_create(cls, pk="doi", **kwargs):
        """
        This function will try to get the article by doi.

        If the article exists update, otherwise create.

        The kwargs must be a dict, something like this:

            {
                "doi": "10.1016/J.JFOODENG.2017.08.999",
                "id_int_production": '',
                "title": "Update the record",
                "number": "999",
                "volume": "9",
                "year": 2002,
                "source": "SUCUPIRA",
                "journal": instance of <journal>
                "contributors": list of <contributors> [<contributor>, <contributor>, <contributor>]
                "license": instance of license
            }

        return article(object), 0|1

        0 = updated
        1 = created

        """
        if not kwargs.get("doi") and not kwargs.get("id_int_production"):
            raise ValueError("Param doi or id_int_production is required")

        if pk == "doi":
            filter = {"doi": kwargs.get("doi")}
        elif pk == "id_int_production":
            filter = {"id_int_production": kwargs.get("id_int_production")}

        try:
            article = cls.objects.get(**filter)
            created = 0
        except ScholarlyArticles.DoesNotExist:
            article = cls.objects.create()
            created = 1
    
        article.doi = kwargs.get("doi")
        article.id_int_production = kwargs.get("id_int_production")
        article.title = kwargs.get("title")
        article.number = kwargs.get("number")
        article.volume = kwargs.get("volume")
        article.year = kwargs.get("year")
        article.source = kwargs.get("source")
        article.journal = kwargs.get("journal")
        article.save()

        for contrib in kwargs.get("contributors"):
            article.contributors.add(contrib)

        return article, created
        

class Journals(models.Model):
    journal_issn_l = models.CharField(_("ISSN-L"), max_length=50, null=True, blank=True)
    journal_issns = models.CharField(_("ISSN's"), max_length=50, null=True, blank=True)
    journal_name = models.CharField(
        _("Journal Name"), max_length=510, null=True, blank=True
    )
    publisher = models.CharField(_("Publisher"), max_length=255, null=True, blank=True)
    journal_is_in_doaj = models.BooleanField(
        _("DOAJ"), default=False, null=True, blank=True
    )

    autocomplete_search_field = "journal_name"

    def autocomplete_label(self):
        return self.journal_name

    def __unicode__(self):
        return self.journal_issn_l or self.journal_issns or self.journal_name

    def __str__(self):
        return self.journal_issn_l or self.journal_issns or self.journal_name

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

    @classmethod
    def get_or_create(cls, pk="journal_issn_l", **kwargs):
        """
        This function will try to get the journal by journal_issn_l or journal__name.

        If the journal exists update, otherwise create.

        The kwargs must be a dict, something like this:

            {
                journal_issn_l = "",
                journal_issns = "",
                journal_name = "",
                publisher = "",
                journal_is_in_doaj = True,
            }

        return journal(object), 0|1

        0 = updated
        1 = created

        """

        if not kwargs.get("journal_issn_l") and not kwargs.get("journal_name"):
            raise ValueError("Param journal_issn_l or journal_name is required")

        if pk == "journal_issn_l":
            filter = {"journal_issn_l": kwargs.get("journal_issn_l")}
        elif pk == "journal_name":
            filter = {"journal_name": kwargs.get("journal_name")}

        try:
            journal = cls.objects.get(**filter)
            created = 0
        except Journals.DoesNotExist:
            journal = cls.objects.create()
            created = 1

        journal.journal_issn_l = kwargs.get("journal_issn_l")
        journal.journal_issns = kwargs.get("journal_issns")
        journal.journal_name = kwargs.get("journal_name")
        journal.publisher = kwargs.get("publisher")
        journal.journal_is_in_doaj = kwargs.get("journal_is_in_doaj")
        journal.save()

        return journal, created


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

    programs = models.ManyToManyField("Program", verbose_name=_("Program"), blank=True)

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
        AutocompletePanel("programs"),
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

        if self.programs:
            d.update(
                {"programs": [program.data for program in self.programs.iterator()]}
            )

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
        return "%s" % self.name

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

    @classmethod
    def get_or_create(cls, **kwargs):
        """
        This function will try to get the affiliation by name.

        If the affiliation exists update, otherwise create.

        The kwargs must be a dict, something like this:

            {
                "name" = "",
                "official": instance of <institution>
                "country": instance of country
            }

        return affiliation(object), 0|1

        0 = updated
        1 = created

        """

        if not kwargs.get("name"):
            raise ValueError("Param name is required")

        filter = {"name": kwargs.get("name")}
 
        try:
            aff = cls.objects.get(**filter)
            created = 0
        except Affiliations.DoesNotExist:
            aff = cls.objects.create()
            created = 1

        aff.name = kwargs.get("name")
        aff.official = kwargs.get("institution")
        aff.country = kwargs.get("country")
        aff.save()

        return aff, created


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
        max_length=100,
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
        max_length=100,
        null=True,
        blank=True,
        help_text=_(
            "Reference to the data, can be id, line. Use line:10 or id:452 to to differ between id|line."
        ),
    )
    data = models.TextField(
        _("Data"),
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

    @classmethod
    def get_or_create(cls, **kwargs):
        """
        This function will try to get the license by name.

        If the license exists update, otherwise create.

        The kwargs must be a dict, something like this:

            {
                "name" = "",
                "delay_in_days": "", 
                "start": "", 
                "url": "", 
            }

        return license(object), 0|1

        0 = updated
        1 = created

        """

        if not kwargs.get("name"):
            raise ValueError("Param name is required")

        filter = {"name": kwargs.get("name")}
 
        try:
            lic = cls.objects.get(**filter)
            created = 0
        except License.DoesNotExist:
            lic = cls.objects.create()
            created = 1

        lic.name = kwargs.get("name")
        lic.delay_in_days = kwargs.get("delay_in_days")
        lic.start = kwargs.get("start")
        lic.url = kwargs.get("url")
        lic.save()

        return lic, created


class Program(models.Model):
    """
    This entity represents the program of an institution.
    Program is associated with the Affiliation that is a proxy to Institution

    Example of programs:

        TECNOLOGIA EM QUÍMICA E BIOQUÍMICA
        LINGUÍSTICA
        INOVAÇÃO E TECNOLOGIA INTEGRADAS À MEDICINA VETERINÁRIA
        ODONTOLOGIA
        BIODIVERSIDADE TROPICAL

    """

    name = models.CharField(_("Program Name"), max_length=510, null=True, blank=True)
    affiliation = models.ForeignKey(
        Affiliations,
        verbose_name=_("Affiliation"),
        on_delete=models.SET_NULL,
        max_length=1020,
        null=True,
        blank=True,
    )

    def autocomplete_label(self):
        return "%s" % self.name

    def __unicode__(self):
        return "%s - %s" % (self.name, self.affiliation or "")

    def __str__(self):
        return self.__unicode__()

    panels = [
        FieldPanel("name"),
        AutocompletePanel("affiliation"),
    ]

    @property
    def data(self):
        d = {
            "program__name": self.name,
        }

        if self.affiliation:
            d.update(self.affiliation.data)

        return d


    @classmethod
    def get_or_create(cls, **kwargs):
        """
        This function will try to get the program by name.

        If the program exists update, otherwise create.

        The kwargs must be a dict, something like this:

            {
                "name" = "",
                "affiliation": instance of affiliation
            }

        return program(object), 0|1

        0 = updated
        1 = created

        """

        if not kwargs.get("name"):
            raise ValueError("Param name is required")

        filter = {"name": kwargs.get("name")}
 
        try:
            prg = cls.objects.get(**filter)
            created = 0
        except Program.DoesNotExist:
            prg = cls.objects.create()
            created = 1

        prg.name = kwargs.get("name")
        prg.affiliation = kwargs.get("affiliation")
        prg.save()

        return prg, created