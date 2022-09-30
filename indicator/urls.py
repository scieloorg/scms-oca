from django.urls import path

from .views import show_graph


app_name = "indicator"

urlpatterns = [
    path("graph/", view=show_graph, name="show_graph"),
]
