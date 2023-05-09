from rest_framework import viewsets

from .serializers import EventSerializer

from event_directory import models


class EventViewSet(viewsets.ModelViewSet):
    serializer_class = EventSerializer
    http_method_names = ['get']
    # queryset = Event.objects.all()

    def get_queryset(self):
        """
        This view should return a list of all published Event.
        """
        # user = self.request.user

        return models.EventDirectory.objects.filter(
            record_status="PUBLISHED"
        ).order_by("-updated")

    # def perform_create(self, serializer):
    #     serializer.save(creator=self.request.user)

    # def post(self, request, *args, **kwargs):
    #     return self.create(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    # def put(self, request, *args, **kwargs):
    #     return self.update(request, *args, **kwargs)

    # def delete(self, request, *args, **kwargs):
    #     return self.destroy(request, *args, **kwargs)
