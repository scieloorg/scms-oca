from django.urls import path

from . import elk_controller
from . import views

urlpatterns = [
    path('', views.indicators_view, name='indicators'),
    path('filters/', elk_controller.get_filters, name='elk_filters'),
    path('indicators/', elk_controller.get_indicators, name='elk_indicators'),
]
