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

    title = indexes.CharField(model_attr="title", null=True)
    doi = indexes.CharField(model_attr="doi", null=True)
    volume = indexes.CharField(model_attr="volume", null=True)
    number = indexes.CharField(model_attr="number", null=True)
    year = indexes.CharField(model_attr="year", null=True)
    is_oa = indexes.CharField(model_attr="is_oa", null=True)
    open_access_status = indexes.CharField(model_attr="open_access_status", null=True)
    apc = indexes.CharField(model_attr="apc", null=True)

    # control fields
    record_type = indexes.CharField(null=False)
    record_status = indexes.CharField(null=True)

    # Foreign key field
    license = indexes.CharField(model_attr="license", null=True)
    journal = indexes.CharField(model_attr="journal", null=True)

    # MultiValue fields
    sources = indexes.MultiValueField(null=True)
    contributors = indexes.MultiValueField(null=True)
    concepts = indexes.MultiValueField(null=True)
    affiliations = indexes.MultiValueField(null=True)
    institutions = indexes.MultiValueField(null=True)
    programs = indexes.MultiValueField(null=True)

    thematic_level_0 = indexes.MultiValueField(null=True)
    thematic_level_1 = indexes.MultiValueField(null=True)
    thematic_level_2 = indexes.MultiValueField(null=True)

    cities = indexes.MultiValueField(null=True)
    states = indexes.MultiValueField(null=True)
    regions = indexes.MultiValueField(null=True)

    text = indexes.CharField(document=True, use_template=True)

    def prepare_record_type(self, obj):
        return "article"

    def prepare_record_status(self, obj):
        return "No Publisher"

    def prepare_sources(self, obj):
        if obj.sources:
            return [s.name for s in obj.sources.all()]

    def prepare_contributors(self, obj):
        if obj.contributors:
            return [
                "%s, %s" % (contrib.family, contrib.given)
                for contrib in obj.contributors.all()
            ]

    def prepare_affiliations(self, obj):
        if obj.contributors:
            affs = []
            for contrib in obj.contributors.all():
                affs.extend([affs.name for affs in contrib.affiliations.all()])
            return set(affs)

    def prepare_institutions(self, obj):
        if obj.contributors:
            insts = []
            for contrib in obj.contributors.all():
                if contrib.affiliations.all():
                    insts.extend(
                        [
                            affs.official.name
                            for affs in contrib.affiliations.all()
                            if affs.official
                        ]
                    )
            return set(insts)

    def prepare_concepts(self, obj):
        if obj.concepts:
            return [c.name for c in obj.concepts.all()]

    def prepare_cities(self, obj):
        cities = set()
        if obj.contributors.all():
            for co in obj.contributors.all():
                if co.affiliations.all():
                    for aff in co.affiliations.all():
                        if aff.official:
                            if aff.official.location:
                                if aff.official.location.city:
                                    cities.add(aff.official.location.city.name)

        return cities

    def prepare_states(self, obj):
        states = set()
        if obj.contributors.all():
            for co in obj.contributors.all():
                if co.affiliations.all():
                    for aff in co.affiliations.all():
                        if aff.official:
                            if aff.official.location:
                                if aff.official.location.state:
                                    states.add(aff.official.location.state.name)
        return states

    def prepare_regions(self, obj):
        regions = set()
        if obj.contributors.all():
            for co in obj.contributors.all():
                if co.affiliations.all():
                    for aff in co.affiliations.all():
                        if aff.official:
                            if aff.official.location:
                                if aff.official.location.state:
                                    if aff.official.location.state.region:
                                        regions.add(aff.official.location.state.region)
        return regions

    def prepare_thematic_level_0(self, obj):
        thematics = set()

        if obj.concepts:
            for c in obj.concepts.all():
                if c.thematic_areas.all():
                    for t in c.thematic_areas.all():
                        thematics.add(t.level0)
        return thematics

    def prepare_thematic_level_1(self, obj):
        thematics = set()

        if obj.concepts:
            for c in obj.concepts.all():
                if c.thematic_areas.all():
                    for t in c.thematic_areas.all():
                        thematics.add(t.level1)
        return thematics

    def prepare_thematic_level_2(self, obj):
        thematics = set()

        if obj.concepts:
            for c in obj.concepts.all():
                if c.thematic_areas.all():
                    for t in c.thematic_areas.all():
                        thematics.add(t.level2)

        return thematics

    def prepare_programs(self, obj):
        return ["AGRONOMIA".title(), "AGRONEGÓCIO".title()]

    def get_model(self):
        return models.Article

    def index_queryset(self, using=None):
        return self.get_model().objects.all()
