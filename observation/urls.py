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
    path(
        "export/start/",
        views.export_start,
        name="export_start",
    ),
    path(
        "export/status/<str:job_id>/",
        views.export_status,
        name="export_status",
    ),
    path(
        "export/download/<str:job_id>/",
        views.export_download,
        name="export_download",
    ),
]
