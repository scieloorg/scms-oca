from django.urls import path

from .views import search_page_by_index, search_view_list

app_name = "search"
urlpatterns = [
    path("page/<str:index_name>/", search_page_by_index, name="search_page_by_index"),
    path("api/search-results-list/", search_view_list, name="search_results_list"),
]
