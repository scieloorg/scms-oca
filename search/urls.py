from django.urls import path

from search import views

app_name = "search"
urlpatterns = [
    # path /
    path("", views.search, name="search"),
]
