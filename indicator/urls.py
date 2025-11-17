from django.urls import path

from . import views

urlpatterns = [
    path('', views.scielo_view, name='indicator_home'),
    path('data/', views.data_view, name='data'),
    path('filters/', views.filters_view, name='filters'),
    path('world/', views.world_view, name='sci_prod_world'),
    path('brazil/', views.brazil_view, name='sci_prod_brazil'),
    path('scielo/', views.scielo_view, name='sci_prod_scielo'),
    path('social/', views.social_view, name='soc_prod'),
    path('journal/', views.journal_metrics_view, name='sci_prod_journal_metrics'),
    path('search/', views.search_item, name='search_item'),
]
