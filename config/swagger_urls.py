from django.urls import include, path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions

public_apis = [ 
    path('api/v1/', include("config.api_router")),  # public endpoints
]

schema_view = get_schema_view(
    openapi.Info(
        title="Directory API",
        default_version='v1',
        description="",
        terms_of_service="https://ocabr.org",
        contact=openapi.Contact(email="ocabr@ocabr.org"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
    patterns=public_apis,
)

# swagger
urlpatterns = [
   path('', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),  # noqa E501
   path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),  # noqa E501
]