from django.urls import path

from .views import filters_view, search_item_view

urlpatterns = [
    path('filters/', filters_view, name='search_gateway_filters'),
    path('search-item/', search_item_view, name='search_gateway_search_item'),
]
