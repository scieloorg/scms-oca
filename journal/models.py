from django.db import models
from django.utils.translation import gettext as _

from core.models import Source


class SourceJournal(models.Model):
    specific_id = models.CharField(
        _("Specific Id"), max_length=255, null=False, blank=False
    )
    issns = models.CharField(_("ISSN"), max_length=255, null=True, blank=False)
    issn_l = models.CharField(_("ISSN_L"), max_length=255, null=True, blank=False)
    country_code = models.CharField(_("Country Code"), max_length=255, null=True, blank=False)
    title = models.CharField(_("Title"), max_length=1024, null=True, blank=False)
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
                    "issns",
                ]
            ),
            models.Index(
                fields=[
                    "issn_l",
                ]
            ),
            models.Index(
                fields=[
                    "specific_id",
                ]
            ),
            models.Index(
                fields=[
                    "title",
                ]
            ),
        ]

    def __unicode__(self):
        return str("%s") % (self.issns or self.specific_id)

    def __str__(self):
        return str("%s") % (self.issns or self.specific_id)

    @property
    def has_specific_id(self):
        return bool(self.specific_id)

    @classmethod
    def get(cls, **kwargs):
        """
        This function will try to get the source journal by attributes:

            * issn
            * specific_id

        The kwargs must be a dict, something like this:

            {
                "specific_id": "https://openalex.org/sources/S183843087",
                "issn": "1234-5678",
                "source": OPENALEX,
            }

        return source journal|None

        This function can raise:
            ValueError
            SourceJournal.DoesNotExist
            SourceJournal.MultipleObjectsReturned
        """

        filters = {}

        if (
            not kwargs.get("issn")
            and not kwargs.get("specific_id")
            and not kwargs.get("source")
        ):
            raise ValueError("Param issn or specific_id is required")

        if kwargs.get("specific_id"):
            filters = {
                "specific_id": kwargs.get("specific_id"),
                "source": kwargs.get("source"),
            }
        elif kwargs.get("issn"):
            filters = {"issn": kwargs.get("issn"), "source": kwargs.get("source")}

        return cls.objects.get(**filters)


    @classmethod
    def create_or_update(cls, **kwargs):
        """
        This function will try to get the journal by issn.

        If the journal exists update, otherwise create.

        The kwargs must be a dict, something like this:

            {
                "issns": "1234-5678, 0987-6543",
                "issn_l": "1987-9373",
                "country_code": "BR",
                "title": "Update the record",
                "number": "999",
                "volume": "9",
                "sources": list of <sources> [<source>, <source>]
            }

        return journal(object), 0|1

        0 = updated
        1 = created

        """

        try:
            journal = cls.get(**kwargs)
            created = 0
        except SourceJournal.DoesNotExist:
            journal = cls.objects.create()
            created = 1
        except SourceJournal.MultipleObjectsReturned as e:
            print(_("The source journal table have duplicity...."))
            raise (SourceJournal.MultipleObjectsReturned)

        journal.issns = kwargs.get("issns")
        journal.issn_l = kwargs.get("issn_l")
        journal.title = kwargs.get("title")
        journal.country_code = kwargs.get("country_code")
        journal.specific_id = kwargs.get("specific_id")
        journal.updated = kwargs.get("updated")
        journal.created = kwargs.get("created")
        journal.raw = kwargs.get("raw")
        journal.source = kwargs.get("source")
        journal.save()

        return journal, created