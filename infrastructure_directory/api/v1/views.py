from rest_framework import viewsets

from .serializers import InfrastructureSerializer

from infrastructure_directory import models


class InfrastructureViewSet(viewsets.ModelViewSet):
    serializer_class = InfrastructureSerializer
    http_method_names = ['get']
    # queryset = Infrastructure.objects.all()

    def get_queryset(self):
        """
        This view should return a list of all published Infrastructure.
        """
        # user = self.request.user

        return models.InfrastructureDirectory.objects.filter(
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
