from wagtail.admin.panels import FieldPanel
from wagtail_modeladmin.options import (
    ModelAdmin
)
from .models import Chart


class ChartAdmin(ModelAdmin):
    model = Chart
    menu_label = "Gráficos"
    menu_icon = "bar-chart"
    list_display = ("title", "scope", "chart_type")
    search_fields = ("label", "scope", "title")

    panels = [
        FieldPanel("title"),
        FieldPanel("label"),
        FieldPanel("scope"),
        FieldPanel("menu_scope"),
        FieldPanel("chart_type"),
        FieldPanel("iframe_url"),
        FieldPanel("link_chart"),
        FieldPanel("image"),
        FieldPanel("data_zip"),
    ]

# modeladmin_register(ChartAdmin)
