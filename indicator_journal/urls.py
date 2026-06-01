from django.urls import path

from . import views

app_name = "indicator_journal"

urlpatterns = [
    path("profile-options/", views.journal_profile_options_view, name="profile_options"),
]
