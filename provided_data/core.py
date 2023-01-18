from django.db import models
from django.utils.translation import gettext as _

from wagtailautocomplete.edit_handlers import AutocompletePanel
from wagtail.admin.edit_handlers import FieldPanel

from core.models import CommonControlField
from core.forms import CoreAdminModelForm

from .choices import DOCUMENT_TYPES, NAME_TYPES, LEVELS


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


class Name(models.Model):
    text = models.CharField(_("Text"), max_length=255, null=True, blank=True)
    type = models.CharField(_("Type"), choices=NAME_TYPES, max_length=20, null=True, blank=True)

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
            models.Index(fields=['type', ]),
        ]

    panels = [
        FieldPanel('text'),
        FieldPanel('type'),
    ]

    @property
    def data(self):
        return {
            'name__text': self.text,
            'name__type': self.type,
        }

    @classmethod
    def create(cls, text, type):

        name = cls()
        name.text = text
        name.type = type
        name.save()

        return name

    base_form_class = CoreAdminModelForm


class ResearchArea(models.Model):
    text = models.CharField(_("Text"), max_length=100, null=True, blank=True)
    level = models.CharField(_("Level"), choices=LEVELS, max_length=20, null=True, blank=True, default="UNDEFINED")

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
            models.Index(fields=['level', ]),
        ]

    panels = [
        FieldPanel('text'),
        FieldPanel('level'),
    ]

    @property
    def data(self):
        return {
            'research_area__text': self.text,
            'research_area__level': self.level,
        }

    @classmethod
    def get_or_create(cls, text, level):
        try:
            research_area = cls.objects.filter(text=text, level=level)[0]
        except IndexError:
            research_area = cls()
            research_area.text = text
            research_area.type = level
            research_area.save()

        return research_area

    base_form_class = CoreAdminModelForm


class CommonPublicationData(CommonControlField):
    entity_id = models.CharField(_("Entity ID"), max_length=50, null=True, blank=True)
    keywords = models.ManyToManyField("CommonTextField", verbose_name=_("Keywords"), blank=True)
    document_titles = models.ManyToManyField("CommonTextField", verbose_name=_("Titles"), related_name='+', blank=True)
    authors = models.ManyToManyField("Authorship", verbose_name=_("Authors"), blank=True)
    publication_date = models.CharField(_("Publication Date"), max_length=10, null=True, blank=True)
    document_type = models.CharField(_("Document type"), choices=DOCUMENT_TYPES, max_length=50, null=True, blank=True)
    language = models.CharField(_("Language"), max_length=50, null=True, blank=True)
    research_areas = models.ManyToManyField(ResearchArea, verbose_name=_("Research area"), related_name='+', blank=True)
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
        AutocompletePanel('keywords'),
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
            'common_publication_data__keywords': [k.data for k in self.keywords.iterator()],
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
                common_publication.keywords.add(CommonTextField.create(keyword))
            for document_title in document_titles or []:
                common_publication.document_titles.add(CommonTextField.create(document_title))
            for author in authors or []:
                common_publication.authors.add(author)
            common_publication.publication_date = publication_date
            common_publication.document_type = document_type
            common_publication.language = language
            for research_area in research_areas or []:
                common_publication.research_areas.add(ResearchArea.get_or_create(text=research_area, level=None))
            common_publication.start_page = start_page
            common_publication.end_page = end_page
            common_publication.volume = volume
            common_publication.save()

        return common_publication

    base_form_class = CoreAdminModelForm
