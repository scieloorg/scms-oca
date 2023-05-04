from django.conf import settings
from rest_framework.routers import DefaultRouter, SimpleRouter

from infrastructure_directory.api.v1.views import InfrastructureViewSet

if settings.DEBUG:
    router = DefaultRouter()
else:
    router = SimpleRouter()

router.register("infrastructure", InfrastructureViewSet, basename="Infrastructure")

app_name = "api"
urlpatterns = router.urls
