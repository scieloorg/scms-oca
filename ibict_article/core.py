from django.db import models
from django.utils.translation import gettext as _

from wagtail.admin.edit_handlers import FieldPanel
from wagtailautocomplete.edit_handlers import AutocompletePanel

from core.models import CommonControlField
from core.forms import CoreAdminModelForm

from .choices import TYPES
from usefulmodels.models import City, State, Country


class GenericField(models.Model):
    text = models.CharField(_("Text"), max_length=510, null=True, blank=True)

    autocomplete_search_field = 'text'

    def autocomplete_label(self):
        return self.text

    def __unicode__(self):
        return f'{self.text}'

    def __str__(self):
        return f'{self.text}'

    class Meta:
        indexes = [
            models.Index(fields=['text', ]),
        ]

    panels = [
        FieldPanel('text'),
    ]

    @property
    def data(self):
        return {
            'generic_field__text': self.text,
        }

    @classmethod
    def get_or_create(cls, text):

        try:
            generic_fields = cls.objects.filter(text=text)
            generic_field = generic_fields[0]
        except IndexError:
            generic_field = GenericField()
            generic_field.text = text
            generic_field.save()

        return generic_field

    base_form_class = CoreAdminModelForm


class Authorship(models.Model):
    name = models.ManyToManyField("GenericField", verbose_name=_("Name"), blank=True)
    citation_name = models.ManyToManyField("GenericField", verbose_name=_("Citation name"), related_name='+', blank=True)
    research_area = models.ManyToManyField("GenericField", verbose_name=_("Research area"), related_name='+', blank=True)
    birth_city = models.ForeignKey(City, verbose_name=_("Birth city"), on_delete=models.SET_NULL, max_length=100,
                                   null=True, blank=True)
    birth_state = models.ForeignKey(State, verbose_name=_("Birth state"), on_delete=models.SET_NULL, max_length=100,
                                    null=True, blank=True)
    birth_country = models.ForeignKey(Country, verbose_name=_("Birth country"), on_delete=models.SET_NULL,
                                      max_length=100, null=True, blank=True)
    id_lattes = models.CharField(_("Lattes ID"), max_length=50, null=True, blank=True)
    orcid = models.CharField(_("ORCID"), max_length=50, null=True, blank=True)

    autocomplete_search_field = 'name'

    def autocomplete_label(self):
        return self.name

    def __unicode__(self):
        return f'{self.id_lattes}'

    def __str__(self):
        return f'{self.id_lattes}'

    class Meta:
        indexes = [
            models.Index(fields=['id_lattes', ]),
            models.Index(fields=['orcid', ]),
        ]

    panels = [
        AutocompletePanel('name'),
        AutocompletePanel('citation_name'),
        AutocompletePanel('research_area'),
        FieldPanel('birth_city'),
        FieldPanel('birth_state'),
        FieldPanel('birth_country'),
        FieldPanel('id_lattes'),
        FieldPanel('orcid'),
    ]

    @property
    def data(self):
        d = {
            'authorship__name': [n.data for n in self.name.iterator()],
            'authorship__citation_name': [c.data for c in self.citation_name.iterator()],
            'authorship__research_area': [r.data for r in self.research_area.iterator()],
            'authorship__id_lattes': self.id_lattes,
            'authorship__orcid': self.orcid,
        }
        if self.birth_city:
            d.update(self.birth_city.data)
        if self.birth_state:
            d.update(self.birth_state.data)
        if self.birth_country:
            d.update(self.birth_country.data)
        return d

    @classmethod
    def authorship_get_or_create(
            cls,
            user,
            orcid,
            id_lattes,
            names,
            citation_names,
            research_areas,
            birth_city,
            birth_state,
            birth_country
    ):

        try:
            authorships = cls.objects.filter(orcid=orcid, id_lattes=id_lattes)
            authorship = authorships[0]
        except IndexError:
            authorship = cls()
            authorship.save()
            authorship.orcid = orcid
            authorship.id_lattes = id_lattes
            for name in names or []:
                authorship.name.add(GenericField.get_or_create(name))
            for citation_name in citation_names or []:
                authorship.citation_name.add(GenericField.get_or_create(citation_name))
            for research_area in research_areas or []:
                authorship.research_area.add(GenericField.get_or_create(research_area))
            authorship.birth_city = City.get_or_create(user=user, name=birth_city)
            authorship.birth_state = State.get_or_create(user=user, name=birth_state)
            authorship.birth_country = Country.get_or_create(user=user, name_pt=birth_country, name_en=birth_country)
            authorship.save()

        return authorship

    base_form_class = CoreAdminModelForm


