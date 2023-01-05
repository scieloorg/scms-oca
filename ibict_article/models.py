from django.db import models
from django.utils.translation import gettext as _

from wagtail.admin.edit_handlers import FieldPanel
from wagtailautocomplete.edit_handlers import AutocompletePanel

from core.forms import CoreAdminModelForm
from core.models import CommonControlField
from .choices import TYPES
from .core import GenericField, GenericArticle, Authorship


class JournalArticle(GenericArticle):
    series = models.CharField(_("Series"), max_length=100, null=True, blank=True)
    issn = models.ManyToManyField(GenericField, verbose_name=_("ISSN's"), related_name='+', blank=True)
    journal_title = models.ManyToManyField(GenericField, verbose_name=_("Journal title"), related_name='+', blank=True)

    def __unicode__(self):
        return f'{self.journal_title}'

    def __str__(self):
        return f'{self.journal_title}'

    class Meta:
        indexes = [
            models.Index(fields=['series', ]),
        ]

    panels = GenericArticle.panels + [
        FieldPanel('series'),
        AutocompletePanel('issn'),
        AutocompletePanel('journal_title'),
    ]

    @property
    def data(self):
        return {
            'generic_article__entity_id': self.entity_id,
            'generic_article__keyword': [k.data for k in self.keyword.iterator()],
            'generic_article__document_title': [t.data for t in self.title.iterator()],
            'generic_article__authors': [a.data for a in self.author.iterator()],
            'generic_article__publication_date': self.publication_date,
            'generic_article__document_type': self.document_type,
            'generic_article__language': self.language,
            'generic_article__research_area': [r.data for r in self.research_area.iterator()],
            'generic_article__start_page': self.start_page,
            'generic_article__end_page': self.end_page,
            'generic_article__volume': self.volume,
            'journal_article__series': self.series,
            'journal_article__issn': [i.data for i in self.issn.iterator()],
            'journal_article__journal_title': [j.data for j in self.journal_title.iterator()],
        }

    @classmethod
    def journal_get_or_create(
            cls,
            user,
            entity_id,
            keyword,
            document_title,
            authors,
            publication_date,
            document_type,
            language,
            research_area,
            start_page,
            end_page,
            volume,
            series,
            issn,
            journal_title
    ):
        try:
            articles = cls.objects.filter(entity_id=entity_id)
            article = articles[0]
        except IndexError:
            article = cls()
            article.creator = user
            article.save()
            article.entity_id = entity_id
            for item in keyword or []:
                article.keyword.add(GenericField.get_or_create(item))
            for item in document_title or []:
                article.document_title.add(GenericField.get_or_create(item))
            for item in authors or []:
                article.authors.add(item)
            article.publication_date = publication_date
            article.document_type = document_type
            article.language = language
            for item in research_area or []:
                article.research_area.add(GenericField.get_or_create(item))
            article.start_page = start_page
            article.end_page = end_page
            article.volume = volume
            article.series = series
            for item in issn or []:
                article.issn.add(GenericField.get_or_create(item))
            for item in journal_title or []:
                article.journal_title.add(GenericField.get_or_create(item))
            article.save()

        return article

    base_form_class = CoreAdminModelForm


class ConferenceProceedings(GenericArticle):

    def __unicode__(self):
        return f'{self.entity_id}'

    def __str__(self):
        return f'{self.entity_id}'

    panels = GenericArticle.panels

    @property
    def data(self):
        return {
            'generic_article__entity_id': self.entity_id,
            'generic_article__keyword': [k.data for k in self.keyword.iterator()],
            'generic_article__document_title': [t.data for t in self.title.iterator()],
            'generic_article__authors': [a.data for a in self.author.iterator()],
            'generic_article__publication_date': self.publication_date,
            'generic_article__document_type': self.document_type,
            'generic_article__language': self.language,
            'generic_article__research_area': [r.data for r in self.research_area.iterator()],
            'generic_article__start_page': self.start_page,
            'generic_article__end_page': self.end_page,
            'generic_article__volume': self.volume
        }

    @classmethod
    def conference_get_or_create(
            cls,
            user,
            entity_id,
            keyword,
            document_title,
            authors,
            publication_date,
            document_type,
            language,
            research_area,
            start_page,
            end_page,
            volume
    ):
        try:
            conferences = cls.objects.filter(entity_id=entity_id)
            conference = conferences[0]
        except IndexError:
            conference = cls()
            conference.creator = user
            conference.save()
            conference.entity_id = entity_id
            for item in keyword or []:
                conference.keyword.add(GenericField.get_or_create(item))
            for item in document_title or []:
                conference.document_title.add(GenericField.get_or_create(item))
            for item in authors or []:
                conference.authors.add(item)
            conference.publication_date = publication_date
            conference.document_type = document_type
            conference.language = language
            for item in research_area or []:
                conference.research_area.add(GenericField.get_or_create(item))
            conference.start_page = start_page
            conference.end_page = end_page
            conference.volume = volume
            conference.save()

        return conference

    base_form_class = CoreAdminModelForm


class Thesis(GenericArticle):
    advisor = models.ManyToManyField(Authorship, verbose_name=_("Advisors"), blank=True)

    def __unicode__(self):
        return f'{self.document_title}'

    def __str__(self):
        return f'{self.document_title}'

    panels = GenericArticle.panels + [
                 AutocompletePanel('advisor'),
             ]

    @property
    def data(self):
        return {
            'generic_article__entity_id': self.entity_id,
            'generic_article__keyword': [k.data for k in self.keyword.iterator()],
            'generic_article__document_title': [t.data for t in self.title.iterator()],
            'generic_article__authors': [a.data for a in self.author.iterator()],
            'generic_article__publication_date': self.publication_date,
            'generic_article__document_type': self.document_type,
            'generic_article__language': self.language,
            'generic_article__research_area': [r.data for r in self.research_area.iterator()],
            'generic_article__start_page': self.start_page,
            'generic_article__end_page': self.end_page,
            'generic_article__volume': self.volume,
            'thesis__advisor': [ad.data for ad in self.advisor.iterator()]
        }

    @classmethod
    def thesis_get_or_create(
            cls,
            user,
            entity_id,
            keyword,
            document_title,
            authors,
            publication_date,
            document_type,
            language,
            research_area,
            start_page,
            end_page,
            volume,
            advisors
    ):
        try:
            theses = cls.objects.filter(entity_id=entity_id)
            thesis = theses[0]
        except IndexError:
            thesis = cls()
            thesis.creator = user
            thesis.save()
            thesis.entity_id = entity_id
            for item in keyword or []:
                thesis.keyword.add(GenericField.get_or_create(item))
            for item in document_title or []:
                thesis.document_title.add(GenericField.get_or_create(item))
            for item in authors or []:
                thesis.authors.add(item)
            thesis.publication_date = publication_date
            thesis.document_type = document_type
            thesis.language = language
            for item in research_area or []:
                thesis.research_area.add(GenericField.get_or_create(item))
            thesis.start_page = start_page
            thesis.end_page = end_page
            thesis.volume = volume
            for item in advisors or []:
                thesis.advisor.add(item)
            thesis.save()

        return thesis

    base_form_class = CoreAdminModelForm


class RawArticle(CommonControlField):
    document_type = models.CharField(_("Document type"), choices=TYPES, max_length=50, null=True, blank=True)
    entity_id = models.CharField(_("Entity ID"), max_length=50, null=True, blank=True)
    json = models.JSONField(_("JSON File"), null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['document_type', ]),
            models.Index(fields=['entity_id', ]),
        ]
