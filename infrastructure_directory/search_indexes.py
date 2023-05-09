# coding: utf-8
from haystack import indexes

from infrastructure_directory import models


class InfraStructureIndex(indexes.SearchIndex, indexes.Indexable):
    """
    Common Fields:
        text
        link
        description
        institutions
        thematic_areas
        Practice
        action
        classification
        keywords
    """

    record_type = indexes.CharField(null=False)
    text = indexes.CharField(document=True, use_template=True)
    title = indexes.CharField(model_attr="title", null=True)
    directory_type = indexes.CharField(null=False)

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
    record_status = indexes.CharField(model_attr="record_status", null=True)

    source = indexes.CharField(model_attr="action", null=True)
    disclaimer = indexes.CharField(null=True)
    institutional_contribution = indexes.CharField(
        model_attr="institutional_contribution", null=True
    )

    def prepare_record_type(self, obj):
        return "directory"

    def prepare_directory_type(self, obj):
        return "infrastructure_directory"

    def prepare_institutions(self, obj):
        if obj.institutions:
            return [institution.name for institution in obj.institutions.all()]

    def prepare_thematic_areas(self, obj):
        thematic_areas = set()
        if obj.thematic_areas:
            for thematic_area in obj.thematic_areas.all():
                thematic_areas.add(thematic_area.level0.strip())
                thematic_areas.add(thematic_area.level1.strip())
                thematic_areas.add(thematic_area.level2.strip())
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
                    regions.add(inst.location.state.region)
                except AttributeError:
                    continue
            return regions

    def prepare_disclaimer(self, obj):
        """
        This add a disclaimer if user.updated is not a company
        user and the content is public
        """

        if obj.updated_by:
            return (
                _("Conteúdo publicado sem moderação / contribuição de %s") % obj.institutional_contribution
                if not obj.updated_by.is_staff and obj.record_status == "PUBLISHED"
                else None
            )

        if obj.creator:
            return (
                _("Conteúdo publicado sem moderação / contribuição de %s") % obj.institutional_contribution
                if not obj.creator.is_staff and obj.record_status == "PUBLISHED"
                else None
            )

    def get_model(self):
        return models.InfrastructureDirectory

    def index_queryset(self, using=None):
        return self.get_model().objects.filter(record_status="PUBLISHED")
