# coding: utf-8
from haystack import indexes

from infrastructure_directory import models
from usefulmodels.models import City, Country

from core.search_indexes import CommonFieldIndex


class InfraStrutureIndex(CommonFieldIndex, indexes.SearchIndex, indexes.Indexable):
    """
    Fields:
        text
    """
    text = indexes.CharField(document=True, use_template=True)
    title = indexes.CharField(model_attr="title", null=True)

    def get_model(self):
        return models.InfrastructureDirectory

    def index_queryset(self, using=None):
        return self.get_model().objects.all()
