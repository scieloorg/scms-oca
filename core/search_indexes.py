# coding: utf-8
from haystack import indexes

from infrastructure_directory import models
from usefulmodels.models import City, Country


class CommonFieldIndex(object):
    """
    Common Fields:
        link
        description
        institutions
        thematic_areas
        pratice
        action
        classification
        keywords
    """

    link = indexes.CharField(model_attr="link", null=True)
    description = indexes.CharField(model_attr="description", null=True)

    institutions = indexes.MultiValueField(null=True)
    pratice = indexes.CharField(model_attr="pratice", null=True)
    action = indexes.CharField(model_attr="pratice", null=True)
    classification = indexes.CharField(model_attr="classification", null=True)
    keywords = indexes.MultiValueField(null=True)
    countries = indexes.MultiValueField(null=True)
    cities = indexes.MultiValueField(null=True)
    states = indexes.MultiValueField(null=True)
    regions = indexes.MultiValueField(null=True)

    def prepare_institutions(self, obj):
        if obj.institutions:
            return [institution.name for institution in obj.institutions.all()]

    def prepare_thematic_areas(self, obj):
        if obj.thematic_areas:
            return ["%s | %s | %s" % (thematic_area.level0, thematic_area.level1, thematic_area.level2) for thematic_area in obj.thematic_areas.all()]

    def prepare_keywords(self, obj):
        if obj.keywords.names():
            return [name for name in obj.keywords.names()]

    def prepare_countries(self, obj):
        countries = set()
        if obj.institutions.all():
            for inst in obj.institutions.all():
                if inst.location:
                    if inst.location.country:
                        countries.add(inst.location.country.name)
            return countries

    def prepare_cities(self, obj):
        cities = set()
        if obj.institutions.all():
            for inst in obj.institutions.all():
                if inst.location:
                    if inst.location.city:
                        cities.add(inst.location.city.name)
            return cities

    def prepare_states(self, obj):
        states = set()
        if obj.institutions.all():
            for inst in obj.institutions.all():
                if inst.location:
                    if inst.location.state:
                        states.add(inst.location.state.name)
            return states

    def prepare_regions(self, obj):
        regions = set()
        if obj.institutions.all():
            for inst in obj.institutions.all():
                if inst.location:
                    if inst.location.region:
                        regions.add(inst.location.region)
            return regions
