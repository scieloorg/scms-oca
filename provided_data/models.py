from django.db import models
from django.utils.translation import gettext as _

from wagtail.admin.edit_handlers import FieldPanel, InlinePanel, TabbedInterface, ObjectList
from wagtailautocomplete.edit_handlers import AutocompletePanel
from wagtail.core.models import Orderable
from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel

from core.forms import CoreAdminModelForm
from core.models import CommonControlField
from .choices import DOCUMENT_TYPES, REGISTERED
from .core import CommonTextField, CommonPublicationData, Name, ResearchArea
from usefulmodels.models import City, State, Country


class JournalArticle(CommonPublicationData):
    series = models.CharField(_("Series"), max_length=50, null=True, blank=True)
    issns = models.ManyToManyField(CommonTextField, verbose_name=_("ISSN's"), related_name='+', blank=True)
    journal_titles = models.ManyToManyField(CommonTextField, verbose_name=_("Journal title"), related_name='+', blank=True)

    def __unicode__(self):
        return ' | '.join([str(journal_title) for journal_title in self.journal_titles.iterator()])

    def __str__(self):
        return ' | '.join([str(journal_title) for journal_title in self.journal_titles.iterator()])

    class Meta:
        indexes = [
            models.Index(fields=['series', ]),
        ]

    panels = CommonPublicationData.panels + [
        FieldPanel('series'),
        AutocompletePanel('issns'),
        AutocompletePanel('journal_titles'),
    ]

    @property
    def data(self):
        _data = super().data
        _data.update({
                'journal_article__series': self.series,
                'journal_article__issns': [i.data for i in self.issns.iterator()],
                'journal_article__journal_titles': [j.data for j in self.journal_titles.iterator()]
        })
        return _data

    @classmethod
    def journal_get_or_create(
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
            volume,
            series,
            issns,
            journal_titles
    ):
        try:
            article = cls.objects.filter(entity_id=entity_id)[0]
        except IndexError:
            article = super().get_or_create(
                user=user,
                entity_id=entity_id,
                keywords=keywords,
                document_titles=document_titles,
                authors=authors,
                publication_date=publication_date,
                document_type=document_type,
                language=language,
                research_areas=research_areas,
                start_page=start_page,
                end_page=end_page,
                volume=volume
            )
            article.series = series
            for issn in issns or []:
                article.issns.add(CommonTextField.create(issn))
            for journal_title in journal_titles or []:
                article.journal_titles.add(CommonTextField.create(journal_title))
            article.save()

        return article

    base_form_class = CoreAdminModelForm


class ConferenceProceedings(CommonPublicationData):

    def __unicode__(self):
        return f'{self.entity_id}'

    def __str__(self):
        return f'{self.entity_id}'

    panels = CommonPublicationData.panels

    @property
    def data(self):
        return super().data

    @classmethod
    def conference_get_or_create(
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
            conference = cls.objects.filter(entity_id=entity_id)[0]
        except IndexError:
            conference = super().get_or_create(
                user=user,
                entity_id=entity_id,
                keywords=keywords,
                document_titles=document_titles,
                authors=authors,
                publication_date=publication_date,
                document_type=document_type,
                language=language,
                research_areas=research_areas,
                start_page=start_page,
                end_page=end_page,
                volume=volume
            )

        return conference

    base_form_class = CoreAdminModelForm


class Thesis(CommonPublicationData):
    advisors = models.ManyToManyField("Authorship", verbose_name=_("Advisors"), related_name='+', blank=True)

    def __unicode__(self):
        return f'{self.document_titles}'

    def __str__(self):
        return f'{self.document_titles}'

    panels = CommonPublicationData.panels + [
                 AutocompletePanel('advisors'),
             ]

    @property
    def data(self):
        _data = super().data
        _data.update({
            'thesis__advisors': [ad.data for ad in self.advisors.iterator()]
        })
        return _data

    @classmethod
    def thesis_get_or_create(
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
            volume,
            advisors
    ):
        try:
            thesis = cls.objects.filter(entity_id=entity_id)[0]
        except IndexError:
            thesis = super().get_or_create(
                user=user,
                entity_id=entity_id,
                keywords=keywords,
                document_titles=document_titles,
                authors=authors,
                publication_date=publication_date,
                document_type=document_type,
                language=language,
                research_areas=research_areas,
                start_page=start_page,
                end_page=end_page,
                volume=volume
            )
            for advisor in advisors or []:
                thesis.advisors.add(advisor)
            thesis.save()

        return thesis

    base_form_class = CoreAdminModelForm


class Authorship(CommonControlField, ClusterableModel):
    names = models.ManyToManyField("Name", verbose_name=_("Name"), blank=True)
    citation_names = models.ManyToManyField("Name", verbose_name=_("Citation name"), related_name='+', blank=True)
    person_research_areas = models.ManyToManyField("ResearchArea", verbose_name=_("Research area"), related_name='+', blank=True)
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

    panels_identification = [
        AutocompletePanel('names'),
        AutocompletePanel('citation_names'),
        AutocompletePanel('person_research_areas'),
        FieldPanel('birth_city'),
        FieldPanel('birth_state'),
        FieldPanel('birth_country'),
        FieldPanel('id_lattes'),
        FieldPanel('orcid'),
    ]

    panels_journal_article = [
        InlinePanel('journal_article', label=_('Journal Article'), classname="collapsed"),
    ]

    panels_conference_proceedings = [
        InlinePanel('conference_proceedings', label=_('Conference Proceedings'), classname="collapsed"),
    ]

    panels_thesis = [
        InlinePanel('thesis', label=_('Thesis'), classname="collapsed"),
    ]

    edit_handler = TabbedInterface(
        [
            ObjectList(panels_identification, heading=_('Identification')),
            ObjectList(panels_journal_article, heading=_('Journal Article')),
            ObjectList(panels_conference_proceedings, heading=_('Conference Proceedings')),
            ObjectList(panels_thesis, heading=_('Thesis')),
        ]
    )

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
                authorship.names.add(Name.create(text=name, type='name'))
            for citation_name in citation_names or []:
                authorship.citation_names.add(Name.create(text=citation_name, type='citation name'))
            for research_area in person_research_areas or []:
                authorship.person_research_areas.add(ResearchArea.get_or_create(text=research_area, level=None))
            authorship.birth_city = City.get_or_create(user=user, name=birth_city)
            authorship.birth_state = State.get_or_create(user=user, name=birth_state)
            authorship.birth_country = Country.get_or_create(user=user, name_pt=birth_country, name_en=birth_country)
            authorship.save()

        return authorship

    base_form_class = CoreAdminModelForm


class AuthorJournalArticles(Orderable):
    author = ParentalKey(Authorship, on_delete=models.CASCADE, related_name='journal_article')
    document = models.ForeignKey(JournalArticle, verbose_name=_("Journal Article"),
                                 on_delete=models.SET_NULL, max_length=255, null=True, blank=True)
    registered = models.CharField(_("Registered"), max_length=50,
                                  choices=REGISTERED, null=True, blank=True)
    is_oa = models.BooleanField(_("Open Access"), null=True, blank=True)


class AuthorConferenceProceedings(Orderable):
    author = ParentalKey(Authorship, on_delete=models.CASCADE, related_name='conference_proceedings')
    document = models.ForeignKey(ConferenceProceedings, verbose_name=_("Conference Proceedings"),
                                 on_delete=models.SET_NULL, max_length=255, null=True, blank=True)
    registered = models.CharField(_("Registered"), max_length=50,
                                  choices=REGISTERED, null=True, blank=True)
    is_oa = models.BooleanField(_("Open Access"), null=True, blank=True)


class AuthorThesis(Orderable):
    author = ParentalKey(Authorship, on_delete=models.CASCADE, related_name='thesis')
    document = models.ForeignKey(Thesis, verbose_name=_("Thesis"),
                                 on_delete=models.SET_NULL, max_length=255, null=True, blank=True)
    registered = models.CharField(_("Registered"), max_length=50,
                                  choices=REGISTERED, null=True, blank=True)
    is_oa = models.BooleanField(_("Open Access"), null=True, blank=True)


class RawArticle(CommonControlField):
    document_type = models.CharField(_("Document type"), choices=DOCUMENT_TYPES, max_length=50, null=True, blank=True)
    entity_id = models.CharField(_("Entity ID"), max_length=50, null=True, blank=True)
    json = models.JSONField(_("JSON File"), null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['document_type', ]),
            models.Index(fields=['entity_id', ]),
        ]
