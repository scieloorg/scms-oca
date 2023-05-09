from rest_framework import serializers

from event_directory import models

from usefulmodels.api.v1.serializers import (
    PracticeSerializer,
    ActionSerializer,
    ThematicAreaSerializer,
)

from institution.api.v1.serializers import InstitutionsSerializer


class EventSerializer(serializers.ModelSerializer):
    practice = PracticeSerializer(many=False, read_only=True)
    action = ActionSerializer(many=False, read_only=True)
    institutions = InstitutionsSerializer(many=True, read_only=True)
    thematic_areas = ThematicAreaSerializer(many=True, read_only=True)

    class Meta:
        model = models.EventDirectory
        fields = [
            "title",
            "link",
            "description",
            "practice",
            "action",
            "classification",
            "record_status",
            "source",
            "institutions",
            "thematic_areas",
        ]
        datatables_always_serialize = ("id",)
