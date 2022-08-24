# coding: utf-8
from haystack import indexes

from core.search_indexes import CommonFieldIndex
from policy_directory import models


class PolicyIndex(CommonFieldIndex, indexes.SearchIndex, indexes.Indexable):
    """
    Fields:
        text
    """

    text = indexes.CharField(document=True, use_template=True)
    title = indexes.CharField(model_attr="title", null=True)

    def get_model(self):
        return models.PolicyDirectory

    def index_queryset(self, using=None):
        return self.get_model().objects.all()
