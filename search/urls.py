from django.urls import path

from . import citation_views
from .views import search_view_list

app_name = "search"
urlpatterns = [
    path("api/search-results-list/", search_view_list, name="search_results_list"),
    path("api/citation-formats/", citation_views.citation_formats_view, name="citation_formats"),
    path("api/citation-export/", citation_views.citation_export_view, name="citation_export"),
]
