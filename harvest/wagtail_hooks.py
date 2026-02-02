from wagtail.contrib.modeladmin.options import (
    ModelAdmin, ModelAdminGroup, modeladmin_register
)

from .models import HarvestedBooks, HarvestedPreprint, HarvestedSciELOData


class HarvestedPreprintAdmin(ModelAdmin):
    model = HarvestedPreprint
    menu_label = "Preprint"
    menu_icon = "doc-full"
    list_display = ("identifier", "harvest_status", "datestamp", "created")
    search_fields = ("identifier", "source_url")
    list_filter = ("harvest_status", "index_status")


class HarvestedSciELODataAdmin(ModelAdmin):
    model = HarvestedSciELOData
    menu_label = "SciELO Data"
    menu_icon = "doc-full"
    list_display = ("identifier", "harvest_status", "datestamp", "created")
    search_fields = ("identifier", "source_url")
    list_filter = ("harvest_status", "index_status", "type_data")


class HarvestedBooksAdmin(ModelAdmin):
    model = HarvestedBooks
    menu_label = "Books"
    menu_icon = "doc-full"
    list_display = ("identifier","type_data", "harvest_status", "datestamp", "created")
    search_fields = ("identifier", "source_url")
    list_filter = ("harvest_status", "index_status", "type_data")


class HarvestModelAdminGroup(ModelAdminGroup):
    menu_label = "Harvest"
    menu_icon = "download"
    items = (
        HarvestedPreprintAdmin,
        HarvestedSciELODataAdmin,
        HarvestedBooksAdmin,
    )


modeladmin_register(HarvestModelAdminGroup)
