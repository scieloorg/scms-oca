# coding: utf-8
from haystack import indexes

from event_directory import models


class EventIndex(indexes.SearchIndex, indexes.Indexable):
    """
    Fields:
        text
    """

    text = indexes.CharField(document=True, use_template=True)
    event = indexes.CharField(model_attr="event", null=True)

    link = indexes.CharField(model_attr="link", null=True)
    description = indexes.CharField(model_attr="description", null=True)

    institutions = indexes.MultiValueField(null=True)
    practice = indexes.CharField(model_attr="practice", null=True)
    action = indexes.CharField(model_attr="action", null=True)
    classification = indexes.CharField(model_attr="classification", null=True)
    keywords = indexes.MultiValueField(null=True)
    countries = indexes.MultiValueField(null=True)
    cities = indexes.MultiValueField(null=True)
    states = indexes.MultiValueField(null=True)
    regions = indexes.MultiValueField(null=True)
    thematic_areas = indexes.MultiValueField(null=True)

    def prepare_institutions(self, obj):
        if obj.institutions:
            return [institution.name for institution in obj.institutions.all()]

    def prepare_thematic_areas(self, obj):
        thematic_areas = set()
        if obj.thematic_areas:
            for thematic_area in obj.thematic_areas.all():
                thematic_areas.add(thematic_area.level0)
                thematic_areas.add(thematic_area.level1)
                thematic_areas.add(thematic_area.level2)
            return thematic_areas

    def prepare_keywords(self, obj):
        if obj.keywords.names():
            return [name for name in obj.keywords.names()]

    def prepare_countries(self, obj):
        countries = set()
        if obj.institutions.all():
            for inst in obj.institutions.all():
                try:
                    countries.add(inst.location.country.name)
                except AttributeError:
                    continue
            return countries

    def prepare_cities(self, obj):
        cities = set()
        if obj.institutions.all():
            for inst in obj.institutions.all():
                try:
                    cities.add(inst.location.city.name)
                except AttributeError:
                    continue
            return cities

    def prepare_states(self, obj):
        states = set()
        if obj.institutions.all():
            for inst in obj.institutions.all():
                try:
                    states.add(inst.location.state.name)
                except AttributeError:
                    continue
            return states

    def prepare_regions(self, obj):
        regions = set()
        if obj.institutions.all():
            for inst in obj.institutions.all():
                try:
                    regions.add(inst.location.region.name)
                except AttributeError:
                    continue
            return regions

    def get_model(self):
        return models.EventDirectory

    def index_queryset(self, using=None):
        return self.get_model().objects.all()
