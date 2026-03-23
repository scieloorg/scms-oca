from django.urls import path

from . import views

urlpatterns = [
    path('filters/', views.filters_view, name='search_gateway_filters'),
    path('search-item/', views.search_item_view, name='search_gateway_search_item'),
]
