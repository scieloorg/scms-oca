from django.urls import path

from . import citation_views
from .views import search_view_list

app_name = "search"
urlpatterns = [
    path("api/search-results-list/", search_view_list, name="search_results_list"),
    path("api/citation-styles/", citation_views.citation_csl_styles_view, name="citation_csl_styles"),
    path("api/citation-preview/", citation_views.citation_preview_view, name="citation_preview"),
    path("api/citation-custom-style/", citation_views.citation_custom_style_view, name="citation_custom_style"),
    path("api/citation-export/", citation_views.citation_export_view, name="citation_export"),
]
