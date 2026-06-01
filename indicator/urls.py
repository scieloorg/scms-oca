from django.urls import path

from . import views


urlpatterns = [
    path('api/v1/chart-data/', views.chart_data_view, name='chart_data_api'),
]
