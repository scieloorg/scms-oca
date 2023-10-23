from rest_framework import serializers

from institution import models

from location.api.v1.serializers import LocationSerializer


class InstitutionsSerializer(serializers.ModelSerializer):
    location = LocationSerializer(many=False, read_only=True)

    class Meta:
        model = models.Institution
        fields = [
            "name",
            "institution_type",
            "location",
            "acronym",
            "source",
            "level_1",
            "level_2",
            "level_3",
            "url",
        ]
        datatables_always_serialize = ("id",)
