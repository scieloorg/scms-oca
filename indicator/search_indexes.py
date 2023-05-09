# coding: utf-8
import logging

from haystack import indexes

from indicator import models
from indicator.controller import CATEGORIES


class IndicatorIndex(indexes.SearchIndex, indexes.Indexable):
    """
    Fields:
        text
    """

    created = indexes.CharField(model_attr="created", null=False)
    validity = indexes.CharField(model_attr="validity", null=True)

    text = indexes.CharField(document=True, use_template=True)
    record_type = indexes.CharField(null=False)

    title = indexes.CharField(model_attr="title", null=True)
    description = indexes.CharField(model_attr="description", null=True)
    start_date = indexes.CharField(model_attr="start_date_year", null=True)
    end_date = indexes.CharField(model_attr="end_date_year", null=True)
    link = indexes.CharField(model_attr="link", null=True)
    record_status = indexes.CharField(model_attr="record_status", null=True)
    source = indexes.CharField(model_attr="source", null=True)

    object_name = indexes.CharField(model_attr="object_name", null=True)
    category = indexes.CharField(model_attr="category", null=True)
    context = indexes.CharField(model_attr="context", null=True)

    # raw_data = indexes.CharField(null=True)

    # ForeignKeys
    classification = indexes.CharField(null=True)
    action = indexes.CharField(null=True)
    practice = indexes.CharField(null=True)

    # ManyToMany
    keywords = indexes.MultiValueField(null=True)
    thematic_areas = indexes.MultiValueField(null=True)
    institutions = indexes.MultiValueField(null=True)
    locations = indexes.MultiValueField(null=True)

    # Location
    countries = indexes.MultiValueField(null=True)
    cities = indexes.MultiValueField(null=True)
    states = indexes.MultiValueField(null=True)
    regions = indexes.MultiValueField(null=True)

    # prioridade do mais amplo para o mais restrito
    # nacional -> municipal
    geo_priority = indexes.IntegerField(null=True)
    thematic_priority = indexes.IntegerField(null=True)
    # priority = indexes.FloatField(null=True)

    # scopes
    # por enquanto deixar apenas geo_scope, traduzir apenas como "âmbito"
    geo_scope = indexes.CharField(null=True)
    thematic_scope = indexes.CharField(null=True)

    disclaimer = indexes.CharField(null=True)
    slug = indexes.CharField(model_attr="slug", null=True)

    institutional_contribution = indexes.CharField(
        model_attr="institutional_contribution", null=True
    )

    def prepare_geo_priority(self, obj):
        n_institutions = obj.institutions.count()

        cities = set()
        states = set()
        regions = set()

        for item in obj.institutions.iterator():
            if item.location:
                cities.add(item.location.city)
            if item.location and item.location.state:
                states.add(item.location.state)
                regions.add(item.location.state.region)

        for item in obj.locations.iterator():
            if item.city:
                cities.add(item.city)
            if item.state:
                states.add(item.state)
                regions.add(item.state.region)

        n_cities = len(cities)
        n_states = len(states)
        n_regions = len(regions)
        n_country = 1
        return (
            n_country * 1000000
            + n_regions * 100000
            + n_states * 10000
            + n_cities * 1000
            + n_institutions * 100
        )

    def prepare_geo_scope(self, obj):
        cities = set()
        states = set()
        regions = set()

        n_institutions = obj.institutions.count()
        for item in obj.institutions.iterator():
            if item.location:
                cities.add(item.location.city)
            if item.location and item.location.state:
                states.add(item.location.state)
                regions.add(item.location.state.region)

        for item in obj.locations.iterator():
            if item.city:
                cities.add(item.city)
            if item.state:
                states.add(item.state)
                regions.add(item.state.region)

        n_cities = len(cities)
        n_states = len(states)
        n_regions = len(regions)

        scopes = ["INSTITUCIONAL", "MUNICIPAL", "ESTADUAL", "REGIONAL", "NACIONAL"]
        numbers = [n_institutions, n_cities, n_states, n_regions, 1]
        logging.info(numbers)
        for i, number in enumerate(numbers):
            if number:
                scope = scopes[i]
                if number > 1:
                    scope = "INTER" + scope
                logging.info(scope)
                return scope

    def prepare_thematic_priority(self, obj):
        if obj.thematic_areas:
            level0 = set()
            level1 = set()
            level2 = set()
            for thematic_area in obj.thematic_areas.all():
                level0.add(thematic_area.level0)
                level1.add(thematic_area.level1)
                level2.add(thematic_area.level2)
            n_thematic_level2 = len(level2)
            n_thematic_level1 = len(level1)
            n_thematic_level0 = len(level0)
            return (
                n_thematic_level0 * 1000000
                + n_thematic_level1 * 100000
                + n_thematic_level2 * 10000
            )

    def prepare_thematic_scope(self, obj):
        for thematic_area in obj.thematic_areas.iterator():
            if thematic_area.level2:
                return "level2"
            if thematic_area.level1:
                return "level1"
            if thematic_area.level0:
                return "level0"

    # def prepare_priority(self, obj):
    #     return obj.raw_data and obj.raw_data.size

    def prepare_action(self, obj):
        return obj.action_and_practice and obj.action_and_practice.action.name

    def prepare_category(self, obj):
        if obj.category:
            return CATEGORIES[obj.category]["title"]

    def prepare_classification(self, obj):
        return obj.action_and_practice and obj.action_and_practice.classification

    def prepare_practice(self, obj):
        return obj.action_and_practice and obj.action_and_practice.practice.name

    def prepare_record_type(self, obj):
        return "indicator"

    def prepare_institutions(self, obj):
        institutions = set()
        if obj.institutions:
            for institution in obj.institutions.all():
                institutions.add(institution)
            return institutions

    def prepare_keywords(self, obj):
        if obj.keywords.names():
            return [name for name in obj.keywords.names()]

    def prepare_thematic_areas(self, obj):
        if obj.thematic_areas:
            thematic_areas = set()
            for thematic_area in obj.thematic_areas.all():
                # manter granularidade média, ou seja, level1
                thematic_areas.add(thematic_area.level0)
                thematic_areas.add(thematic_area.level1)
                thematic_areas.add(thematic_area.level2)
            return thematic_areas

    def prepare_countries(self, obj):
        countries = set()
        if obj.locations.all():
            for loc in obj.locations.all():
                try:
                    countries.add(loc.country.name)
                except AttributeError:
                    continue
        if obj.institutions.all():
            for inst in obj.institutions.all():
                try:
                    countries.add(inst.location.country.name)
                except AttributeError:
                    continue
        return countries

    def prepare_cities(self, obj):
        cities = set()
        if obj.locations.all():
            for loc in obj.locations.all():
                try:
                    cities.add(loc.city.name)
                except AttributeError:
                    continue
        if obj.institutions.all():
            for inst in obj.institutions.all():
                try:
                    cities.add(inst.location.city.name)
                except AttributeError:
                    continue
        return cities

    def prepare_states(self, obj):
        states = set()
        if obj.locations.all():
            for loc in obj.locations.all():
                try:
                    states.add(loc.state.name)
                except AttributeError:
                    continue
        if obj.institutions.all():
            for inst in obj.institutions.all():
                try:
                    states.add(inst.location.state.name)
                except AttributeError:
                    continue
        return states

    def prepare_regions(self, obj):
        regions = set()
        if obj.locations.all():
            for loc in obj.locations.all():
                try:
                    regions.add(loc.state.region)
                except AttributeError:
                    continue
        if obj.institutions.all():
            for inst in obj.institutions.all():
                try:
                    regions.add(inst.location.states.region)
                except AttributeError:
                    continue
        return regions

    def prepare_disclaimer(self, obj):
        """
        This add a disclaimer if user.updated is not a company
        user and the content is public
        """
        return obj.disclaimer

    def get_model(self):
        return models.Indicator

    def index_queryset(self, using=None):
        return self.get_model().objects.filter(
            validity="CURRENT", record_status="PUBLISHED"
        )
