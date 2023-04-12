from django.db import models
from django.utils.translation import gettext as _

from wagtail.admin.panels import FieldPanel
from wagtailautocomplete.edit_handlers import AutocompletePanel

from core.forms import CoreAdminModelForm
from core.models import CommonControlField
from .choices import DOCUMENT_TYPES
from .core import CommonTextField, CommonPublicationData, Authorship


class JournalArticle(CommonPublicationData):
    series = models.CharField(_("Series"), max_length=50, null=True, blank=True)
    issns = models.ManyToManyField(
        CommonTextField, verbose_name=_("ISSN's"), related_name="+", blank=True
    )
    journal_titles = models.ManyToManyField(
        CommonTextField, verbose_name=_("Journal title"), related_name="+", blank=True
    )

    def __unicode__(self):
        return " | ".join(
            [str(journal_title) for journal_title in self.journal_titles.iterator()]
        )

    def __str__(self):
        return " | ".join(
            [str(journal_title) for journal_title in self.journal_titles.iterator()]
        )

    class Meta:
        indexes = [
            models.Index(
                fields=[
                    "series",
                ]
            ),
        ]

    panels = CommonPublicationData.panels + [
        FieldPanel("series"),
        AutocompletePanel("issns"),
        AutocompletePanel("journal_titles"),
    ]

    @property
    def data(self):
        _data = super().data
        _data.update(
            {
                "journal_article__series": self.series,
                "journal_article__issns": [i.data for i in self.issns.iterator()],
                "journal_article__journal_titles": [
                    j.data for j in self.journal_titles.iterator()
                ],
            }
        )
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
        journal_titles,
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
                volume=volume,
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
        return f"{self.entity_id}"

    def __str__(self):
        return f"{self.entity_id}"

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
        volume,
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
                volume=volume,
            )

        return conference

    base_form_class = CoreAdminModelForm


class Thesis(CommonPublicationData):
    advisors = models.ManyToManyField(
        Authorship, verbose_name=_("Advisors"), blank=True
    )

    def __unicode__(self):
        return f"{self.document_titles}"

    def __str__(self):
        return f"{self.document_titles}"

    panels = CommonPublicationData.panels + [
        AutocompletePanel("advisors"),
    ]

    @property
    def data(self):
        _data = super().data
        _data.update({"thesis__advisors": [ad.data for ad in self.advisors.iterator()]})
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
        advisors,
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
                volume=volume,
            )
            for advisor in advisors or []:
                thesis.advisors.add(advisor)
            thesis.save()

        return thesis

    base_form_class = CoreAdminModelForm


class RawArticle(CommonControlField):
    document_type = models.CharField(
        _("Document type"), choices=DOCUMENT_TYPES, max_length=50, null=True, blank=True
    )
    entity_id = models.CharField(_("Entity ID"), max_length=50, null=True, blank=True)
    json = models.JSONField(_("JSON File"), null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(
                fields=[
                    "document_type",
                ]
            ),
            models.Index(
                fields=[
                    "entity_id",
                ]
            ),
        ]
