from django.db import models
from django.utils.translation import gettext as _
from wagtail.admin.panels import FieldPanel
from wagtailautocomplete.edit_handlers import AutocompletePanel

from institution.models import Institution
from usefulmodels.models import Country

from . import choices
from .forms import ContributorForm


class Journal(models.Model):
    journal_issn_l = models.CharField(_("ISSN-L"), max_length=255, null=True, blank=True)
    journal_issns = models.CharField(_("ISSN's"), max_length=255, null=True, blank=True)
    journal_name = models.CharField(
        _("Journal Name"), max_length=512, null=True, blank=True
    )
    publisher = models.CharField(_("Publisher"), max_length=255, null=True, blank=True)
    journal_is_in_doaj = models.BooleanField(
        _("DOAJ"), default=False, null=True, blank=True
    )

    autocomplete_search_field = "journal_name"

    def autocomplete_label(self):
        return self.journal_name

    def __unicode__(self):
        return self.__str__()

    def __str__(self):
        return self.journal_issn_l or self.journal_issns or self.journal_name or ""

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
    def get(cls, **kwargs):
        """
        This function will try to get the journal by journal_issn_l or journal__name.

        The kwargs must be a dict, something like this:

            {
                journal_issn_l = "",
                journal_issns = "",
                journal_name = "",
                publisher = "",
                journal_is_in_doaj = True,
            }

        return journal|None

        This function can raise: 
            ValueError
            Journal.DoesNotExist
            Journal.MultipleObjectsReturned
        """

        filters = {}

        if not kwargs.get("journal_issn_l") and not kwargs.get("journal_name"):
            raise ValueError("Param journal_issn_l or journal_name is required")

        if kwargs.get("journal_issn_l") == "journal_issn_l":
            filters = {"journal_issn_l": kwargs.get("journal_issn_l")}
        elif kwargs.get("journal_name") == "journal_name":
            filters = {"journal_name__iexact": kwargs.get("journal_name")}

        if kwargs.get("journal_issns"):
            filters["journal_issns__icontains"] = kwargs.get("journal_issns")

        return cls.objects.get(**filters)

    @classmethod
    def create_or_update(cls, **kwargs):
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

        try:
            journal = cls.get(**kwargs)
            created = 0
        except Journal.DoesNotExist:
            journal = cls.objects.create()
            created = 1
        except Journal.MultipleObjectsReturned as e:
            print(_("The Journal table have duplicity...."))
            raise (Journal.MultipleObjectsReturned)

        journal.journal_issn_l = kwargs.get("journal_issn_l")
        journal.journal_issns = kwargs.get("journal_issns")
        journal.journal_name = kwargs.get("journal_name")
        journal.publisher = kwargs.get("publisher")
        journal.journal_is_in_doaj = kwargs.get("journal_is_in_doaj")
        journal.save()

        return journal, created


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
        "Affiliation",
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
    def get(cls, **kwargs):
        """
        This function will try to get the program by name and affiliation.

        The kwargs must be a dict, something like this:

           {
                "name" = "",
                "affiliation": instance of affiliation
           }

        return program|None

        This function can raise: 
            ValueError
            Program.DoesNotExist
            Program.MultipleObjectsReturned
        """

        if not kwargs.get("name"):
            raise ValueError("Param name is required")

        filters = {"name": kwargs.get("name")}

        if kwargs.get("affiliation"):
            filters["affiliation"] = kwargs.get("affiliation")

        return cls.objects.get(**filters)

    @classmethod
    def create_or_update(cls, **kwargs):
        """
        This function will try to get the affiliation by name.

        If the affiliation exists update, otherwise create.

        The kwargs must be a dict, something like this:

            {
                "name" = "",
                "affiliation": instance of affiliation
            }

        return affiliation(object), 0|1

        0 = updated
        1 = created
        """

        try:
            prg = cls.get(**kwargs)
            created = 0
        except Program.DoesNotExist:
            prg = cls.objects.create()
            created = 1
        except Program.MultipleObjectsReturned as e:
            print(_("The program table have duplicity...."))
            raise (Program.MultipleObjectsReturned)

        prg.name = kwargs.get("name")
        prg.affiliation = kwargs.get("affiliation")
        prg.save()

        return prg, created


class Contributor(models.Model):
    family = models.CharField(_("Family Name"), max_length=255, null=True, blank=True)
    given = models.CharField(_("Given Name"), max_length=255, null=True, blank=True)
    orcid = models.CharField("ORCID", max_length=50, null=True, blank=True)
    authenticated_orcid = models.BooleanField(
        _("Authenticated"), default=False, null=True, blank=True
    )
    affiliations = models.ManyToManyField(
        "Affiliation", verbose_name=_("Affiliations"), blank=True
    )
    affiliations_string = models.TextField(_("Affiliation String"), blank=True, null=True,)
    programs = models.ManyToManyField(Program, verbose_name=_("Program"), blank=True)

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
            )
        ]

    panels = [
        FieldPanel("family"),
        FieldPanel("given"),
        FieldPanel("orcid"),
        FieldPanel("authenticated_orcid"),
        FieldPanel("affiliations_string"),
        AutocompletePanel("affiliations"),
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

    @classmethod
    def get(cls, **kwargs):
        """
        This function will try to get the contributor by attributes: 

            * family 
            * given
            * orcid
            * affiliation
            * programs

        The kwargs must be a dict, something like this:

           {
                "name" = "",
                "affiliation": instance of affiliation
           }

        return contributor|None

        This function can raise: 
            ValueError
            Contributor.DoesNotExist
            Contributor.MultipleObjectsReturned
        """
        filters = {}

        if not kwargs.get("family") and not kwargs.get("given"):
            raise ValueError("Param family name, given and affiliations_string is required")

        filters = {
            "family__iexact": kwargs.get("family"),
            "given__iexact": kwargs.get("given"),
        }

        if kwargs.get("orcid"):
            filters["orcid"] = kwargs.get("orcid")
        else:
            filters["orcid"] = None

        if kwargs.get("affiliations_string"):
            filters["affiliations_string"] = kwargs.get("affiliations_string")
        else:
            filters["affiliations_string"] = None

        return cls.objects.get(**filters)
    
    @classmethod
    def create_or_update(cls, **kwargs):
        """
        This function will try to get the contributor by family or given name or orcid.

        If the contributor exists update, otherwise create.

        The kwargs must be a dict, something like this:

            {
                family = "",
                given = "",
                orcid = "",
                authenticated_orcid = True|False,
                affiliations_string: "",
                affiliations: [affiliation, affiliation] (object)
                programs: [program, program] (list of object)
            }

        return contributor(object), 0|1

        0 = updated
        1 = created

        """

        try:
            co = cls.get(**kwargs)
            created = 0
        except Contributor.DoesNotExist:
            co = cls.objects.create()
            created = 1
        except Contributor.MultipleObjectsReturned as e:
            print(_("The contributor table have duplicity...."))
            raise (Contributor.MultipleObjectsReturned)

        co.family = kwargs.get("family")
        co.given = kwargs.get("given")
        co.orcid = kwargs.get("orcid")
        co.affiliations_string = kwargs.get("affiliations_string")
        co.authenticated_orcid = kwargs.get("authenticated_orcid")
        co.save()

        if kwargs.get("programs"):
            for program in kwargs.get("programs"):
                co.programs.add(program)

        if kwargs.get("affiliations"):
            for aff in kwargs.get("affiliations"):
                co.affiliations.add(aff)

        return co, created

    base_form_class = ContributorForm


class Affiliation(models.Model):
    name = models.CharField(
        _("Affiliation Name"), max_length=2048, null=True, blank=True
    )
    official = models.ForeignKey(
        Institution,
        verbose_name=_("Official Affiliation Name"),
        on_delete=models.SET_NULL,
        max_length=1020,
        null=True,
        blank=True,
    )
    # novo campo para non_official (not MEC), aponta para institution
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
        return self.__str__()

    def __str__(self):
        return self.name or ""

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
    def get(cls, **kwargs):
        """
        This function will try to get the affiliation by attributes: 

            * name
            * official institution


        The kwargs must be a dict, something like this:

           {
                "name" = "",
                "affiliation": instance of affiliation
           }

        return affiliation|None

        This function can raise: 
            ValueError
            Affiliation.DoesNotExist
            Affiliation.MultipleObjectsReturned
        """

        if not kwargs.get("name"):
            raise ValueError("Param name is required")

        filters = {"name": kwargs.get("name")}

        if kwargs.get("official"):
            filters["official"] = kwargs.get("official")

        return cls.objects.get(**kwargs)

    @classmethod
    def create_or_update(cls, **kwargs):
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

        try:
            aff = cls.get(**kwargs)
            created = 0
        except Affiliation.DoesNotExist:
            aff = cls.objects.create()
            created = 1
        except Affiliation.MultipleObjectsReturned as e:
            print(_("The affiliation table have duplicity...."))
            raise (Affiliation.MultipleObjectsReturned)

        aff.name = kwargs.get("name")
        aff.official = kwargs.get("official")
        aff.country = kwargs.get("country")
        aff.save()

        return aff, created


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
        _("URL"),
        null=True,
        blank=True,
        help_text="Link to a web page describing this license",
    )

    def __unicode__(self):
        return self.__str__()

    def __str__(self):
        return self.name or self.url

    @classmethod
    def get(cls, **kwargs):
        """
        This function will try to get the license by attributes: 

            * name

        The kwargs must be a dict, something like this:

           {
                "name" = "",
                "license": instance of license
           }

        return license|None

        This function can raise: 
            ValueError
            License.DoesNotExist
            License.MultipleObjectsReturned

        """

        if not kwargs.get("name"):
            raise ValueError("Param name is required")

        filter = {"name": kwargs.get("name")}

        return cls.objects.get(**filter)

    @classmethod
    def create_or_update(cls, **kwargs):
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

        try:
            lic = cls.get(**kwargs)
            created = 0
        except License.DoesNotExist:
            lic = cls.objects.create()
            created = 1
        except License.MultipleObjectsReturned as e:
            print(_("The license table have duplicity...."))
            raise (License.MultipleObjectsReturned)

        lic.name = kwargs.get("name")
        lic.delay_in_days = kwargs.get("delay_in_days")
        lic.start = kwargs.get("start")
        lic.url = kwargs.get("url")
        lic.save()

        return lic, created


class Source(models.Model):
    name = models.CharField(_("Source Name"), max_length=50, null=True, blank=True)

    autocomplete_search_field = "name"

    def autocomplete_label(self):
        return str(self)

    def __unicode__(self):
        return self.__str__()

    def __str__(self):
        return self.name or ""


class SourceArticle(models.Model):
    specific_id = models.CharField(
        _("Specific Id"), max_length=255, null=False, blank=False
    )
    year = models.CharField(_("Year"), max_length=10, null=True, blank=True)
    is_paratext = models.BooleanField(
        _("Paratext"), default=False, null=True, blank=True
    )
    doi = models.CharField(_("DOI"), max_length=100, null=True, blank=False)
    updated = models.CharField(
        _("Source updated date"), max_length=50, null=True, blank=False
    )
    created = models.CharField(
        _("Source created date"), max_length=50, null=True, blank=False
    )
    raw = models.JSONField(_("JSON File"), null=True, blank=True)
    source = models.ForeignKey(
        Source,
        verbose_name=_("Source"),
        null=True,
        on_delete=models.CASCADE,
    )

    class Meta:
        indexes = [
            models.Index(
                fields=[
                    "doi",
                ]
            ),
            models.Index(
                fields=[
                    "specific_id",
                ]
            ),
            models.Index(
                fields=[
                    "year",
                ]
            ),
        ]

    def __unicode__(self):
        return str("%s") % (self.doi or self.specific_id)

    def __str__(self):
        return str("%s") % (self.doi or self.specific_id)

    @property
    def has_doi(self):
        return bool(self.doi)

    @property
    def has_specific_id(self):
        return bool(self.specific_id)

    @classmethod
    def get(cls, **kwargs):
        """
        This function will try to get the source article by attributes: 

            * doi
            * specific_id

        The kwargs must be a dict, something like this:

            {
                "specific_id": "10.1016/J.JFOODENG.2017.08.999",
                "year": "Update the record",
                "is_paratext": "999",
                "doi": "9",
                "source": 2002,
            }

        return source article|None

        This function can raise: 
            ValueError
            SourceArticle.DoesNotExist
            SourceArticle.MultipleObjectsReturned
        """

        filters = {}

        if not kwargs.get("doi") and not kwargs.get("specific_id"):
            raise ValueError("Param doi or specific_id is required")

        if kwargs.get("doi"):
            filters = {"doi": kwargs.get("doi")}
        elif kwargs.get("specific_id"):
            filters = {"specific_id": kwargs.get("specific_id")}

        return cls.objects.get(**filters)

    @classmethod
    def create_or_update(cls, **kwargs):
        """
        This function will try to get the article by doi.

        If the article exists update, otherwise create.

        The kwargs must be a dict, something like this:

            {
                "doi": "10.1016/J.JFOODENG.2017.08.999",
                "title": "Update the record",
                "number": "999",
                "volume": "9",
                "year": 2002,
                "journal": instance of <journal>
                "contributors": list of <contributors> [<contributor>, <contributor>, <contributor>]
                "license": instance of license
                "sources": list of <sources> [<source>, <source>]
            }

        return article(object), 0|1

        0 = updated
        1 = created

        """

        try:
            article = cls.get(**kwargs)
            created = 0
        except SourceArticle.DoesNotExist:
            article = cls.objects.create()
            created = 1
        except SourceArticle.MultipleObjectsReturned as e:
            print(_("The source article table have duplicity...."))
            raise (SourceArticle.MultipleObjectsReturned)

        article.doi = kwargs.get("doi")
        article.specific_id = kwargs.get("specific_id")
        article.is_paratext = kwargs.get("is_paratext")
        article.year = kwargs.get("year")
        article.updated = kwargs.get("updated")
        article.created = kwargs.get("created")
        article.raw = kwargs.get("raw")
        article.source = kwargs.get("source")
        article.save()

        return article, created


class Article(models.Model):
    title = models.CharField(_("Title"), max_length=510, null=True, blank=True)
    doi = models.CharField(_("DOI"), max_length=100, null=True, blank=True)
    volume = models.CharField(_("Volume"), max_length=20, null=True, blank=True)
    number = models.CharField(_("Number"), max_length=20, null=True, blank=True)
    year = models.CharField(_("Year"), max_length=20, null=True, blank=True)
    is_ao = models.BooleanField(
        _("Is Open Access"), default=False, null=True, blank=True
    )
    open_access_status = models.CharField(
        _("Open Access Status"),
        max_length=50,
        choices=choices.OA_STATUS,
        null=True,
        blank=True,
    )
    license = models.ForeignKey(
        License,
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
        Contributor, verbose_name=_("Contributors"), blank=True
    )
    journal = models.ForeignKey(
        Journal,
        verbose_name=_("Journals"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    sources = models.ManyToManyField(
        Source,
        verbose_name=_("Source"),
        blank=True,
    )

    def __unicode__(self):
        return self.__str__()

    def __str__(self):
        return self.doi or self.title

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
                    "apc",
                ]
            ),
            models.Index(
                fields=[
                    "journal",
                ]
            ),
        ]

    panels = [
        FieldPanel("title"),
        FieldPanel("doi"),
        FieldPanel("volume"),
        FieldPanel("number"),
        FieldPanel("year"),
        FieldPanel("open_access_status"),
        FieldPanel("license"),
        FieldPanel("apc"),
        AutocompletePanel("contributors"),
        AutocompletePanel("journal"),
        AutocompletePanel("sources"),
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
            "article__license": self.license.name if self.license else "",
            "article__apc": self.apc,
            "article__contributors": [
                contributor.data for contributor in self.contributors.iterator()
            ],
            "article__sources": [source.name for source in self.sources.all()],
        }

        if self.journal:
            d.update(self.journal.data)

        return d

    @classmethod
    def get(cls, **kwargs):
        """
        This function will try to get the article by attributes: 

            * doi

        The kwargs must be a dict, something like this:

            {
                "doi": "10.1016/J.JFOODENG.2017.08.999",
                "title": "Update the record",
                "number": "999",
                "volume": "9",
                "year": 2002,
                "journal": instance of <journal>
                "contributors": list of <contributors> [<contributor>, <contributor>, <contributor>]
                "license": instance of license
                "sources": list of <sources> [<source>, <source>]
            }

        return article|None

        This function can raise: 
            ValueError
            Article.DoesNotExist
            Article.MultipleObjectsReturned
        """

        if not kwargs.get("doi") and not kwargs.get("title"):
            raise ValueError("Param doi or title is required")

        if kwargs.get("doi"):
            filters = {"doi": kwargs.get("doi")}

        if kwargs.get("title"):
            filters = {"title": kwargs.get("title")}

        return cls.objects.get(**filters)

    @classmethod
    def create_or_update(cls, pk="doi", **kwargs):
        """
        This function will try to get the article by doi.

        If the article exists update, otherwise create.

        The kwargs must be a dict, something like this:

            {
                "doi": "10.1016/J.JFOODENG.2017.08.999",
                "title": "Update the record",
                "number": "999",
                "volume": "9",
                "year": 2002,
                "journal": instance of <journal>
                "contributors": list of <contributors> [<contributor>, <contributor>, <contributor>]
                "license": instance of license
                "sources": list of <sources> [<source>, <source>]
            }

        return article(object), 0|1

        0 = updated
        1 = created

        """

        try:
            article = cls.get(**kwargs)
            created = 0
        except Article.DoesNotExist:
            article = cls.objects.create()
            created = 1
        except SourceArticle.MultipleObjectsReturned as e:
            print(_("The article table have duplicity...."))
            raise (Article.MultipleObjectsReturned)

        article.doi = kwargs.get("doi")
        article.title = kwargs.get("title")
        article.number = kwargs.get("number")
        article.volume = kwargs.get("volume")
        article.year = kwargs.get("year")
        article.is_ao = kwargs.get("is_ao")
        article.journal = kwargs.get("journal")
        article.license = kwargs.get("license")
        article.apc = kwargs.get("apc")
        article.open_access_status = kwargs.get("open_access_status")
        article.save()

        if kwargs.get("contributors"):
            for contrib in kwargs.get("contributors"):
                article.contributors.add(contrib)

        if kwargs.get("sources"):
            for source in kwargs.get("sources"):
                article.sources.add(source)

        return article, created