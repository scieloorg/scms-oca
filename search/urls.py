from django.urls import path

from search import views
from .views import get_search_results_json, search_view_list

app_name = "search"
urlpatterns = [
    # path /
    path("", views.search, name="search"),
    path(
        "detail/<str:indicator_slug>",
        views.indicator_detail,
        name="indicator_detail",
    ),
    path(
        "indicator/<str:indicator_slug>/summarized/",
        views.indicator_summarized,
        name="indicator_summarized",
    ),
    path(
        "indicator/<str:indicator_slug>/raw_data/",
        views.indicator_raw_data,
        name="indicator_raw_data",
    ),
    path(
        "graph/", views.graph, name="graph"
    ),
    path(
        "graph/json", views.graph_json, name="graph_json"
    ),
    path(
        "graph/context_facet", views.context_facet, name="context_facet"
    ),
    path("api/search-results/", get_search_results_json, name="search_results_elastic_json"),
    path("api/search-results-list/", search_view_list, name="search_results_list"),
]
