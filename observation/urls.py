from django.urls import path

from . import views

app_name = "observation"

urlpatterns = [
    path(
        "list/",
        views.list,
        name="list",
    ),
    path(
        "filters/",
        views.filters,
        name="filters",
    ),
    path(
        "table/",
        views.table,
        name="table",
    ),
]
