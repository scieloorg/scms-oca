from rest_framework import viewsets

from .serializers import EducationSerializer

from education_directory import models


class EducationViewSet(viewsets.ModelViewSet):
    serializer_class = EducationSerializer
    http_method_names = ["get"]
    # queryset = Education.objects.all()

    def get_queryset(self):
        """
        This view should return a list of all published Education.
        """
        # user = self.request.user

        return models.EducationDirectory.objects.filter(
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
