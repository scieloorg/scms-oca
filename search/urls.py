from django.urls import path
from search import views

from .views import (
    get_filters_for_data_source,
    search_view_list,
)

app_name = "search"

urlpatterns = [
    path("api/search-results-list/", search_view_list, name="search_results_list"),
    path("api/filters/", get_filters_for_data_source, name="get_filters_for_data_source"),
]
