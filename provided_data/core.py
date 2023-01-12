from django.db import models
from django.utils.translation import gettext as _

from wagtail.admin.edit_handlers import FieldPanel
from wagtailautocomplete.edit_handlers import AutocompletePanel
from taggit.managers import TaggableManager

from core.models import CommonControlField
from core.forms import CoreAdminModelForm

from .choices import DOCUMENT_TYPES, NAME_TYPES, LEVELS
from usefulmodels.models import City, State, Country


class CommonTextField(models.Model):
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
            'common_text_field__text': self.text,
        }

    @classmethod
    def create(cls, text):

        common_text_field = cls()
        common_text_field.text = text
        common_text_field.save()

        return common_text_field

    base_form_class = CoreAdminModelForm


class Authorship(models.Model):
    names = models.ManyToManyField("CommonTextField", verbose_name=_("Name"), blank=True)
    citation_names = models.ManyToManyField("CommonTextField", verbose_name=_("Citation name"), related_name='+', blank=True)
    person_research_areas = models.ManyToManyField("CommonTextField", verbose_name=_("Research area"), related_name='+', blank=True)
    birth_city = models.ForeignKey(City, verbose_name=_("Birth city"), on_delete=models.SET_NULL, max_length=100,
                                   null=True, blank=True)
    birth_state = models.ForeignKey(State, verbose_name=_("Birth state"), on_delete=models.SET_NULL, max_length=100,
                                    null=True, blank=True)
    birth_country = models.ForeignKey(Country, verbose_name=_("Birth country"), on_delete=models.SET_NULL,
                                      max_length=100, null=True, blank=True)
    id_lattes = models.CharField(_("Lattes ID"), max_length=50, null=True, blank=True)
    orcid = models.CharField(_("ORCID"), max_length=50, null=True, blank=True)

    autocomplete_search_field = 'names'

    def autocomplete_label(self):
        return self.names

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
        AutocompletePanel('names'),
        AutocompletePanel('citation_names'),
        AutocompletePanel('person_research_areas'),
        FieldPanel('birth_city'),
        FieldPanel('birth_state'),
        FieldPanel('birth_country'),
        FieldPanel('id_lattes'),
        FieldPanel('orcid'),
    ]

    @property
    def data(self):
        d = {
            'authorship__names': [n.data for n in self.names.iterator()],
            'authorship__citation_names': [c.data for c in self.citation_name.iterator()],
            'authorship__person_research_areas': [r.data for r in self.research_area.iterator()],
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
            person_research_areas,
            birth_city,
            birth_state,
            birth_country
    ):

        try:
            authorship = cls.objects.filter(orcid=orcid, id_lattes=id_lattes)[0]
        except IndexError:
            authorship = cls()
            authorship.save()
            authorship.orcid = orcid
            authorship.id_lattes = id_lattes
            for name in names or []:
                authorship.names.add(CommonTextField.create(name))
            for citation_name in citation_names or []:
                authorship.citation_names.add(CommonTextField.create(citation_name))
            for research_area in person_research_areas or []:
                authorship.person_research_areas.add(CommonTextField.create(research_area))
            authorship.birth_city = City.get_or_create(user=user, name=birth_city)
            authorship.birth_state = State.get_or_create(user=user, name=birth_state)
            authorship.birth_country = Country.get_or_create(user=user, name_pt=birth_country, name_en=birth_country)
            authorship.save()

        return authorship

    base_form_class = CoreAdminModelForm


class CommonPublicationData(CommonControlField):
    entity_id = models.CharField(_("Entity ID"), max_length=50, null=True, blank=True)
    keywords = TaggableManager(_("Keywords"), blank=True)
    document_titles = models.ManyToManyField("CommonTextField", verbose_name=_("Titles"), related_name='+', blank=True)
    authors = models.ManyToManyField("Authorship", verbose_name=_("Authors"), blank=True)
    publication_date = models.CharField(_("Publication Date"), max_length=10, null=True, blank=True)
    document_type = models.CharField(_("Document type"), choices=TYPES, max_length=50, null=True, blank=True)
    language = models.CharField(_("Language"), max_length=50, null=True, blank=True)
    research_areas = models.ManyToManyField(CommonTextField, verbose_name=_("Research area"), related_name='+', blank=True)
    start_page = models.CharField(_("Start page"), max_length=10, null=True, blank=True)
    end_page = models.CharField(_("End page"), max_length=10, null=True, blank=True)
    volume = models.CharField(_("Volume"), max_length=50, null=True, blank=True)

    def __unicode__(self):
        return ' | '.join(str(document_title) for document_title in self.document_titles)

    def __str__(self):
        return ' | '.join(str(document_title) for document_title in self.document_titles)

    class Meta:
        indexes = [
            models.Index(fields=['entity_id', ]),
            models.Index(fields=['publication_date', ]),
            models.Index(fields=['document_type', ]),
            models.Index(fields=['language', ]),
            models.Index(fields=['start_page', ]),
            models.Index(fields=['end_page', ]),
            models.Index(fields=['volume', ]),
        ]

    panels = [
        FieldPanel('entity_id'),
        FieldPanel('keywords'),
        AutocompletePanel('document_titles'),
        AutocompletePanel('authors'),
        FieldPanel('publication_date'),
        FieldPanel('document_type'),
        FieldPanel('language'),
        AutocompletePanel('research_areas'),
        FieldPanel('start_page'),
        FieldPanel('end_page'),
        FieldPanel('volume'),
    ]

    @property
    def data(self):
        return {
            'common_publication_data__entity_id': self.entity_id,
            'common_publication_data__keywords': [k.data for k in self.keywords.names()],
            'common_publication_data__document_titles': [t.data for t in self.document_titles.iterator()],
            'common_publication_data__authors': [a.data for a in self.authors.iterator()],
            'common_publication_data__publication_date': self.publication_date,
            'common_publication_data__document_type': self.document_type,
            'common_publication_data__language': self.language,
            'common_publication_data__research_areas': [r.data for r in self.research_areas.iterator()],
            'common_publication_data__start_page': self.start_page,
            'common_publication_data__end_page': self.end_page,
            'common_publication_data__volume': self.volume,
        }

    @classmethod
    def get_or_create(
            cls,
            user,
            entity_id,
            keywords,
            document_titles,
            authors,
            publication_date,
            document_type,
            language,
            research_areas,
            start_page,
            end_page,
            volume
    ):
        try:
            common_publication = cls.objects.filter(entity_id=entity_id)[0]
        except IndexError:
            common_publication = cls()
            common_publication.creator = user
            common_publication.save()
            common_publication.entity_id = entity_id
            for keyword in keywords or []:
                common_publication.keywords.add(keyword)
            for document_title in document_titles or []:
                common_publication.document_titles.add(CommonTextField.create(document_title))
            for author in authors or []:
                common_publication.authors.add(author)
            common_publication.publication_date = publication_date
            common_publication.document_type = document_type
            common_publication.language = language
            for research_area in research_areas or []:
                common_publication.research_areas.add(CommonTextField.create(research_area))
            common_publication.start_page = start_page
            common_publication.end_page = end_page
            common_publication.volume = volume
            common_publication.save()

        return common_publication

    base_form_class = CoreAdminModelForm
