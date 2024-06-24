from django.urls import path
from django.views.generic import TemplateView

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
        "graph/", views.graph, name="graph"
    ),

    path(
        "graph/json", views.graph_json, name="graph_json"
    ),

]
