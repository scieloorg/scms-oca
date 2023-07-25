
# coding: utf-8
from haystack import indexes
from django.conf import settings
from django.utils.translation import gettext as _

from article import models


class SourceArticleIndex(indexes.SearchIndex, indexes.Indexable):
    """
    Fields:
        doi
        year
        source
        title
        record_type
        record_status
        text 
    """
    doi = indexes.CharField(model_attr="doi", null=True)
    year = indexes.CharField(model_attr="year", null=True)
    source = indexes.CharField(model_attr="source", null=True)

    title = indexes.CharField(null=True)
    record_type = indexes.CharField(null=False)
    record_status = indexes.CharField(null=True)

    text = indexes.CharField(document=True, use_template=True)

    def prepare_record_type(self, obj):
        return "SourceArticle"

    def prepare_record_status(self, obj):
        return "No Publisher"

    def prepare_institutions(self, obj):
        if obj.institutions:
            return [institution.name for institution in obj.institutions.all()]
        
    def prepare_title(self,obj):
        return ""

    def get_model(self):
        return models.SourceArticle

    def index_queryset(self, using=None):
        return self.get_model().objects.all()
