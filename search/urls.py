from django.urls import path

from search import views

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
        "graph/json", views.graph, name="graph_json"
    ),
]
