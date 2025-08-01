# coding: utf-8
import random
from haystack import indexes
from django.conf import settings
from django.utils.translation import gettext as _

from policy_directory import models


class PolicyIndex(indexes.SearchIndex, indexes.Indexable):
    """
    Fields:
        text
    """

    # Common fields between directory and article
    # record_type = indexes.CharField(null=False)
    record_status = indexes.CharField(model_attr="record_status", null=True)
    institutions = indexes.MultiValueField(null=True)
    cities = indexes.MultiValueField(null=True)
    states = indexes.MultiValueField(null=True)
    regions = indexes.MultiValueField(null=True)
    thematic_level_0 = indexes.MultiValueField(null=True)
    publication_year = indexes.CharField(index_fieldname="publication_year", null=True)

    text = indexes.CharField(document=True, use_template=True)
    title = indexes.CharField(model_attr="title", null=True)
    directory_type = indexes.CharField(null=False)

    link = indexes.CharField(model_attr="link", null=True)
    date = indexes.CharField(model_attr="date", null=True)
    description = indexes.CharField(model_attr="description", null=True)

    practice = indexes.CharField(model_attr="practice", null=True)
    action = indexes.CharField(model_attr="action", null=True)
    classification = indexes.CharField(model_attr="classification", null=True)
    # keywords = indexes.MultiValueField(null=True)
    countries = indexes.MultiValueField(null=True)

    source = indexes.CharField(model_attr="action", null=True)

    institutional_contribution = indexes.CharField(
        model_attr="institutional_contribution", null=True
    )
    # Universe
    universe = indexes.MultiValueField(null=True)

    # Scope
    scope = indexes.MultiValueField(null=True)

    # Database
    database = indexes.MultiValueField(null=True)

    # Pipeline
    pipeline = indexes.CharField(null=True)

    # Graphs
    graphs = indexes.MultiValueField(null=True)

    type = indexes.CharField(null=True)

    # control fields
    created = indexes.CharField(null=False)
    updated = indexes.CharField(null=False)
    creator = indexes.CharField(null=False)
    updated_by = indexes.CharField(null=False)

    def prepare_publication_year(self, obj):
        if obj.date:
            return obj.date.year
        else: 
            return random.randint(2014, 2023)

    
    def prepare_created(self, obj):
        return obj.created.isoformat()

    def prepare_updated(self, obj):
        return obj.updated.isoformat()
    
    def prepare_creator(self, obj):
        if obj.creator:
            return obj.creator.username
        
    def prepare_updated_by(self, obj):
        if obj.updated_by:
            return obj.updated_by.username

    def prepare_type(self, obj):
        return "directory"

    def prepare_universe(self, obj):
        return ["brazil"]

    def prepare_scope(self, obj):
        return ["Politica"]

    def prepare_database(self, obj):
        return ["ocabr"]
    
    def prepare_pipeline(self, obj):
        return "oca"

    def prepare_graphs(self, obj):
        return [
            "thematic_level_0",
        ]

    def prepare_directory_type(self, obj):
        return "diretório de politica"

    def prepare_institutions(self, obj):
        if obj.institutions:
            return [institution.name for institution in obj.institutions.all()]

    def prepare_thematic_level_0(self, obj):
        thematic_areas = set()
        if obj.thematic_areas:
            for thematic_area in obj.thematic_areas.all():
                thematic_areas.add(thematic_area.level0)
                thematic_areas.add(thematic_area.level1)
                thematic_areas.add(thematic_area.level2)
            return thematic_areas

    # def prepare_keywords(self, obj):
    #     if obj.keywords.names():
    #         return [name for name in obj.keywords.names()]

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
                    regions.add(inst.location.state.region)
                except AttributeError:
                    continue
            return regions

    def prepare_disclaimer(self, obj):
        """
        This add a disclaimer if user.updated is not a company
        user and the content is public
        """
        if obj.institutional_contribution != settings.DIRECTORY_DEFAULT_CONTRIBUTOR:
            if obj.updated_by:
                return (
                    _("Conteúdo publicado sem moderação / contribuição de %s")
                    % obj.institutional_contribution
                    if not obj.updated_by.is_staff and obj.record_status == "PUBLISHED"
                    else None
                )

            if obj.creator:
                return (
                    _("Conteúdo publicado sem moderação / contribuição de %s")
                    % obj.institutional_contribution
                    if not obj.creator.is_staff and obj.record_status == "PUBLISHED"
                    else None
                )

    def get_model(self):
        return models.PolicyDirectory

    def index_queryset(self, using=None):
        return self.get_model().objects.filter(record_status="PUBLISHED")
