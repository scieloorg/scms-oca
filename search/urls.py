from django.urls import path

from .views import search_view_list

app_name = "search"
urlpatterns = [
    path("api/search-results-list/", search_view_list, name="search_results_list"),
]
