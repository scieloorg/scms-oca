from django.urls import path

from . import views

urlpatterns = [
    path('filters/', views.filters_view, name='search_gateway_filters'),
    path('search-item/', views.search_item_view, name='search_gateway_search_item'),
    path('search-as-you-type/', views.search_as_you_type_view, name='search_gateway_search_as_you_type'),
]
