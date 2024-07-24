# coding: utf-8
from haystack import indexes
from django.conf import settings
from django.utils.translation import gettext as _

from education_directory import models


class EducationIndex(indexes.SearchIndex, indexes.Indexable):
    """
    Fields:
        text
    """

    # Common fields between directory and article
    record_type = indexes.CharField(null=False)
    record_status = indexes.CharField(model_attr="record_status", null=True)
    institutions = indexes.MultiValueField(null=True)
    cities = indexes.MultiValueField(null=True)
    states = indexes.MultiValueField(null=True)
    regions = indexes.MultiValueField(null=True)
    thematic_level_0 = indexes.MultiValueField(null=True)
    year = indexes.CharField(null=True)

    text = indexes.CharField(document=True, use_template=True)
    title = indexes.CharField(model_attr="title", null=True)
    directory_type = indexes.CharField(null=False)

    link = indexes.CharField(model_attr="link", null=True)
    description = indexes.CharField(model_attr="description", null=True)

    start_date = indexes.CharField(model_attr="start_date", null=True)
    end_date = indexes.CharField(model_attr="end_date", null=True)
    start_time = indexes.CharField(model_attr="start_time", null=True)
    end_time = indexes.CharField(model_attr="end_time", null=True)

    practice = indexes.CharField(model_attr="practice", null=True)
    action = indexes.CharField(model_attr="action", null=True)
    classification = indexes.CharField(model_attr="classification", null=True)
    keywords = indexes.MultiValueField(null=True)
    countries = indexes.MultiValueField(null=True)

    source = indexes.CharField(model_attr="action", null=True)

    disclaimer = indexes.CharField(null=True)
    institutional_contribution = indexes.CharField(
        model_attr="institutional_contribution", null=True
    )

    # control fields
    created = indexes.CharField(null=False)
    updated = indexes.CharField(null=False)
    creator = indexes.CharField(null=False)
    updated_by = indexes.CharField(null=False)

    def prepare_year(self, obj):
        if obj.start_date:
            return obj.start_date.year
        
        if obj.end_date:
            return obj.end_date.year

    def prepare_created(self, obj):
        return obj.created.isoformat()

    def prepare_updated(self, obj):
        return obj.updated.isoformat()
    
    def prepare_creator(self, obj):
        return obj.creator

    def prepare_record_type(self, obj):
        return "directory"

    def prepare_directory_type(self, obj):
        return "education_directory"

    def prepare_institutions(self, obj):
        if obj.institutions:
            return [institution.name for institution in obj.institutions.all()]

    def prepare_thematic_level_0(self, obj):
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
        return models.EducationDirectory

    def index_queryset(self, using=None):
        return self.get_model().objects.filter(record_status="PUBLISHED")
