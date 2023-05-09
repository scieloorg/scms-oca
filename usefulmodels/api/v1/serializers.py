from rest_framework import serializers

from usefulmodels import models


class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = models.City
        fields = [
            "name",
        ]
        datatables_always_serialize = ("id",)


class StateSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.State
        fields = [
            "name",
            "acronym",
            "region",
        ]
        datatables_always_serialize = ("id",)


class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Country
        fields = [
            "name_pt",
            "name_en",
            "capital",
            "acron3",
            "acron2",
        ]
        datatables_always_serialize = ("id",)


class PracticeSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Practice
        fields = [
            "name",
            "code",
        ]
        datatables_always_serialize = ("id",)


class ActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Action
        fields = [
            "name",
            "code",
        ]
        datatables_always_serialize = ("id",)


class ThematicAreaSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.ThematicArea
        fields = [
            "level0",
            "level1",
            "level2",
        ]
        datatables_always_serialize = ("id",)
