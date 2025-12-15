from django.urls import path

from . import views

urlpatterns = [
    path('', views.indicator_view, {'data_source_name': 'scielo'}, name='indicator_home'),
    path('data/', views.data_view, name='data'),
    path('journal-metrics/', views.journal_metrics_view, name='indicator_journal_metrics'),
    path('journal-metrics/timeseries/', views.journal_metrics_timeseries_view, name='indicator_journal_metrics_timeseries'),
    path('periodical/timeseries/', views.periodical_timeseries_view, name='indicator_periodical_timeseries'),
    path('<str:data_source_name>/', views.indicator_view, name='indicator'),
]
