from rest_framework import serializers

from location import models

from usefulmodels.api.v1.serializers import (
    CitySerializer,
    StateSerializer,
    CountrySerializer,
)


class LocationSerializer(serializers.ModelSerializer):
    city = CitySerializer(many=False, read_only=True)
    state = StateSerializer(many=False, read_only=True)
    country = CountrySerializer(many=False, read_only=True)

    class Meta:
        model = models.Location
        fields = [
            "city",
            "state",
            "country",
        ]
        datatables_always_serialize = ("id",)
