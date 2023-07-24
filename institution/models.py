from django.db import models
from django.utils.translation import gettext as _
from modelcluster.models import ClusterableModel
from wagtail.admin.panels import FieldPanel
from wagtailautocomplete.edit_handlers import AutocompletePanel

from core.models import CommonControlField
from location.models import Location

from . import choices
from .forms import InstitutionForm

from core.models import Source


class Institution(CommonControlField, ClusterableModel):
    name = models.CharField(_("Name"), max_length=255, null=True, blank=True)
    institution_type = models.CharField(
        _("Institution Type"),
        choices=choices.inst_type,
        max_length=255,
        null=True,
        blank=True,
    )

    location = models.ForeignKey(
        Location, null=True, blank=True, on_delete=models.SET_NULL
    )

    acronym = models.CharField(
        _("Acronym to the institution"), blank=True, null=True, max_length=255
    )

    source = models.CharField(
        _("Institution Source"), max_length=255, null=True, blank=True
    )

    level_1 = models.CharField(
        _("Level 1 organization"), blank=True, null=True, max_length=255
    )

    level_2 = models.CharField(
        _("Level 2 organization"), blank=True, null=True, max_length=255
    )

    level_3 = models.CharField(
        _("Level 3 organization"), blank=True, null=True, max_length=255
    )

    url = models.URLField("url", blank=True, null=True)

    logo = models.ImageField(_("Logo"), blank=True, null=True)

    autocomplete_search_field = "name"

    panels = [
        FieldPanel("name"),
        FieldPanel("acronym"),
        FieldPanel("institution_type"),
        AutocompletePanel("location"),
        FieldPanel("source"),
        FieldPanel("level_1"),
        FieldPanel("level_2"),
        FieldPanel("level_3"),
        FieldPanel("url"),
        FieldPanel("logo"),
    ]

    def __unicode__(self):
        return "%s - %s: %s" % (self.name, self.source, self.location)

    def __str__(self):
        return "%s - %s: %s" % (self.name, self.source, self.location)

    def autocomplete_label(self):
        return "%s (%s): %s" % (self.name, self.source, self.location)

    @property
    def data(self):
        d = {
            "institution__name": self.name,
            "institution__type": self.institution_type,
            "institution__acronym": self.acronym,
            "institution__source": self.source,
            "institution__level_1": self.level_1,
            "institution__level_2": self.level_2,
            "institution__level_3": self.level_3,
            "institution__url": self.url,
        }
        if self.location:
            d.update(self.location.data)
        return d

    @classmethod
    def get_or_create(
        cls, inst_name, location_country, location_state, location_city, user
    ):
        # Institution
        # check if exists the institution
        if cls.objects.filter(name=inst_name).exists():
            return cls.objects.get(name=inst_name)
        else:
            institution = cls()
            institution.name = inst_name
            institution.creator = user

            institution.location = Location.get_or_create(
                user, location_country, location_state, location_city
            )

            institution.save()
        return institution
    
    @classmethod
    def get(cls, **kwargs):
        """
        This function will try to get the institution by attributes: 

            * name 
            * institution_type
            * acronym
            * source

        The kwargs must be a dict, something like this:

           {
                "name" = "Institution",
                "institution_type": "agência de apoio à pesquisa",
                "location": location(object),
                "source": "MEC|ROR|..."
           }

        return instition|None

        This function can raise: 
            ValueError
            Institution.DoesNotExist
            Institution.MultipleObjectsReturned
        """
        filters = {}

        if not kwargs.get("name") and not kwargs.get("location") and not kwargs.get("source"):
            raise ValueError("Param name and location(object) and source are required")

        filters = {
            "name__iexact": kwargs.get("name"),
            "source__iexact": kwargs.get("source"),
            "location": kwargs.get("location"),
        }

        return cls.objects.get(**filters)


    @classmethod
    def create_or_update(cls, **kwargs):
        """
        This function will try to get the institution by name and source and location

        If the institution exists update, otherwise create.

        The kwargs must be a dict, something like this:

           {
                "name" = "Institution",
                "institution_type": "agência de apoio à pesquisa",
                "location": location(object),
                "source": "MEC|ROR|..."
                "acronym": "inst"
           }

        return institution(object), 0|1

        0 = updated
        1 = created

        """

        try:
            inst = cls.get(**kwargs)
            created = 0
        except Institution.DoesNotExist:
            inst = cls.objects.create()
            created = 1
        except Institution.MultipleObjectsReturned as e:
            print(_("The institution table have duplicity...."))
            raise (Institution.MultipleObjectsReturned)

        inst.name = kwargs.get("name")
        inst.source = kwargs.get("given")
        inst.location = kwargs.get("orcid")
        inst.acronym = kwargs.get("acronym")
        inst.institution_type = kwargs.get("institution_type")
        inst.save()

        return inst, created


    base_form_class = InstitutionForm


class InstitutionSource(models.Model):
    specific_id = models.CharField(
            _("Specific Id"), max_length=255, null=False, blank=False
        )
    display_name = models.CharField(_("Display Name"), max_length=50, null=True, blank=True)
    updated = models.CharField(
        _("Source updated date"), max_length=50, null=True, blank=False
    )
    created = models.CharField(
        _("Source created date"), max_length=50, null=True, blank=False
    )
    source = models.ForeignKey(
        Source,
        verbose_name=_("Source"),
        null=True,
        on_delete=models.CASCADE,
    )
    raw = models.JSONField(_("JSON Data institution"), null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(
                fields=[
                    "specific_id",
                ]
            ),
            models.Index(
                fields=[
                    "display_name",
                ]
            ),
        ]

    def __unicode__(self):
        return str("%s") % (self.specific_id or self.display_name)

    def __str__(self):
        return str("%s") % (self.specific_id or self.display_name)
 

    @classmethod
    def get(cls, **kwargs):
        """
        This function will try to get the source institution by attributes: 

            * specific_id

        The kwargs must be a dict, something like this:

            {
                "specific_id": "10.1016/J.JFOODENG.2017.08.999",
                "display_name": "Institution ....",
                "source": "OpenAlex",
            }

        return InstitutionSource|None

        This function can raise: 
            ValueError
            InstitutionSource.DoesNotExist
            InstitutionSource.MultipleObjectsReturned
        """

        filters = {}

        if not kwargs.get("specific_id") and not kwargs.get("source"):
            raise ValueError("Param specific_id or source is required")

        if kwargs.get("specific_id"):
            filters = {"specific_id": kwargs.get("doi")}
        elif kwargs.get("source"):
            filters = {"source": kwargs.get("source")}

        return cls.objects.get(**filters)

    @classmethod
    def create_or_update(cls, **kwargs):
        """
        This function will try to get the article by doi.

        If the article exists update, otherwise create.

        The kwargs must be a dict, something like this:

            {
                "specific_id", 
                "display_name",
                "updated", 
                "created", 
                "source", 
                "raw", 
            }

        return InstitutionSource(object), 0|1

        0 = updated
        1 = created

        """

        try:
            inst = cls.get(**kwargs)
            created = 0
        except InstitutionSource.DoesNotExist:
            inst = cls.objects.create()
            created = 1
        except InstitutionSource.MultipleObjectsReturned as e:
            print(_("The source institution table have duplicity...."))
            raise (InstitutionSource.MultipleObjectsReturned)

        inst.specific_id = kwargs.get("specific_id")
        inst.display_name = kwargs.get("display_name")
        inst.updated = kwargs.get("updated")
        inst.created = kwargs.get("created")
        inst.raw = kwargs.get("raw")
        inst.source = kwargs.get("source")
        inst.save()

        return inst, created
