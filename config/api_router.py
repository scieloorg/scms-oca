from django.conf import settings
from rest_framework.routers import DefaultRouter, SimpleRouter

from infrastructure_directory.api.v1.views import InfrastructureViewSet
from education_directory.api.v1.views import EducationViewSet
from event_directory.api.v1.views import EventViewSet
from policy_directory.api.v1.views import PolicyViewSet

if settings.DEBUG:
    router = DefaultRouter()
else:
    router = SimpleRouter()

router.register("infrastructure", InfrastructureViewSet, basename="Infrastructure")
router.register("education", EducationViewSet, basename="Education")
router.register("event", EventViewSet, basename="Event")
router.register("policy", PolicyViewSet, basename="Policy")

app_name = "api"
urlpatterns = router.urls
