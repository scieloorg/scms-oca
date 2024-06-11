# coding: utf-8
from haystack import indexes
from django.conf import settings
from django.utils.translation import gettext as _

from article import models


LICENSE = [
    "cc-by",
    "cc-by-nc",
    "cc-by-nc-nd",
    "cc-by-nc-sa",
    "cc-by-sa",
    "cc-by-nd",
    "cc0",
]


class ArticleIndex(indexes.SearchIndex, indexes.Indexable):
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
    type = indexes.CharField(model_attr="type", null=True)
    year = indexes.CharField(model_attr="year", null=True)
    is_oa = indexes.CharField(model_attr="is_oa", null=True)
    open_access_status = indexes.CharField(model_attr="open_access_status", null=True)
    apc = indexes.CharField(model_attr="apc", null=True)

    # control fields
    record_type = indexes.CharField(null=False)
    record_status = indexes.CharField(null=True)

    # Foreign key field
    license = indexes.CharField(null=True)
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

    # control fields
    created = indexes.CharField(null=False)
    updated = indexes.CharField(null=False)
    creator = indexes.CharField(null=False)
    updated_by = indexes.CharField(null=False)

    def prepare(self, obj):
        self.prepared_data = super(ArticleIndex, self).prepare(obj)

        contributors = obj.contributors.all().prefetch_related("affiliations")
        concepts = obj.concepts.all().prefetch_related("thematic_areas")

        self.prepared_data["contributors"] = self._prepare_contributors(contributors)
        self.prepared_data["affiliations"] = self._prepare_affiliations(contributors)
        self.prepared_data["institutions"] = self._prepare_institutions(contributors)
        self.prepared_data["cities"] = self._prepare_cities(contributors)
        self.prepared_data["states"] = self._prepare_states(contributors)
        self.prepared_data["regions"] = self._prepare_regions(contributors)
        self.prepared_data["concepts"] = self._prepare_concepts(concepts)
        self.prepared_data["thematic_level_0"] = self._prepare_thematic_level_0(
            concepts
        )
        self.prepared_data["thematic_level_1"] = self._prepare_thematic_level_1(
            concepts
        )
        self.prepared_data["thematic_level_2"] = self._prepare_thematic_level_2(
            concepts
        )

        return self.prepared_data

    def prepare_created(self, obj):
        return obj.created.isoformat()

    def prepare_updated(self, obj):
        return obj.updated.isoformat()

    def prepare_creator(self, obj):
        return obj.creator

    def prepare_updated_by(self, obj):
        return obj.updated_by

    def prepare_record_type(self, obj):
        return "article"

    def prepare_record_status(self, obj):
        return "No Publisher"

    def prepare_sources(self, obj):
        if obj.sources:
            return [s.name for s in obj.sources.all()]

    def prepare_license(self, obj):
        if obj.license:
            if obj.license.name in LICENSE:
                return obj.license
            else:
                return "others"

    def _prepare_contributors(self, contributors):

        if contributors:
            return [
                "%s, %s" % (contrib.family, contrib.given) for contrib in contributors
            ]

    def _prepare_affiliations(self, contributors):

        if contributors:
            affs = []
            for contrib in contributors.all():
                affs.extend([affs.name for affs in contrib.affiliations.all()])
            return set(affs)

    def _prepare_institutions(self, contributors):

        if contributors:
            insts = []
            for contrib in contributors:
                if contrib.affiliations.all():
                    insts.extend(
                        [
                            affs.official.name
                            for affs in contrib.affiliations.all()
                            if affs.official
                        ]
                    )
            return set(insts)

    def _prepare_concepts(self, concepts):

        if concepts:
            return [c.name for c in concepts]

    def _prepare_cities(self, contributors):
        cities = set()

        if contributors:
            for co in contributors:
                if co.affiliations.all():
                    for aff in co.affiliations.all():
                        if aff.official:
                            if aff.official.location:
                                if aff.official.location.city:
                                    cities.add(aff.official.location.city.name)

        return cities

    def _prepare_states(self, contributors):
        states = set()

        if contributors:
            for co in contributors:
                if co.affiliations.all():
                    for aff in co.affiliations.all():
                        if aff.official:
                            if aff.official.location:
                                if aff.official.location.state:
                                    states.add(aff.official.location.state.name)
        return states

    def _prepare_regions(self, contributors):
        regions = set()

        if contributors:
            for co in contributors:
                if co.affiliations.all():
                    for aff in co.affiliations.all():
                        if aff.official:
                            if aff.official.location:
                                if aff.official.location.state:
                                    if aff.official.location.state.region:
                                        regions.add(aff.official.location.state.region)
        return regions

    def _prepare_thematic_level_0(self, concepts):
        thematics = set()

        if concepts:
            for c in concepts:
                if c.thematic_areas.all():
                    for t in c.thematic_areas.all():
                        thematics.add(t.level0)
        return thematics

    def _prepare_thematic_level_1(self, concepts):
        thematics = set()

        if concepts:
            for c in concepts:
                if c.thematic_areas.all():
                    for t in c.thematic_areas.all():
                        thematics.add(t.level1)
        return thematics

    def _prepare_thematic_level_2(self, concepts):
        thematics = set()

        if concepts:
            for c in concepts:
                if c.thematic_areas.all():
                    for t in c.thematic_areas.all():
                        thematics.add(t.level2)

        return thematics

    def prepare_programs(self, obj):
        return []

    def get_model(self):
        return models.Article

    def index_queryset(self, using=None):
        return self.get_model().objects.all()
