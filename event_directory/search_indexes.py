# coding: utf-8
from haystack import indexes

from core.search_indexes import CommonFieldIndex
from event_directory import models


class EventIndex(CommonFieldIndex, indexes.SearchIndex, indexes.Indexable):
    """
    Fields:
        text
    """

    text = indexes.CharField(document=True, use_template=True)
    event = indexes.CharField(model_attr="event", null=True)

    def get_model(self):
        return models.EventDirectory

    def index_queryset(self, using=None):
        return self.get_model().objects.all()
