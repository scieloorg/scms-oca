from wagtail.contrib.modeladmin.options import (
    ModelAdmin,
    ModelAdminGroup,
    modeladmin_register,
)

from .models import HarvestedBooks, HarvestedPreprint, HarvestedSciELOData


class HarvestedPreprintModelAdmin(ModelAdmin):
    model = HarvestedPreprint
    menu_label = "Preprint"
    list_display = ("identifier", "harvest_status", "datestamp", "created")
    search_fields = ("identifier", "source_url")
    list_filter = ("harvest_status", "index_status")


class HarvestedSciELODataModelAdmin(ModelAdmin):
    model = HarvestedSciELOData
    menu_label = "SciELO Data"
    list_display = ("identifier", "harvest_status", "datestamp", "created")
    search_fields = ("identifier", "source_url")
    list_filter = ("harvest_status", "index_status", "type_data")


class HarvestedBooksModelAdmin(ModelAdmin):
    model = HarvestedBooks
    menu_label = "Books"
    list_display = ("identifier", "harvest_status", "datestamp", "created")
    search_fields = ("identifier", "source_url")
    list_filter = ("harvest_status", "index_status", "type_data")


class HarvestAdminGroup(ModelAdminGroup):
    menu_label = "Harvest"
    menu_icon = "download"
    items = (
        HarvestedPreprintModelAdmin,
        HarvestedSciELODataModelAdmin,
        HarvestedBooksModelAdmin,
    )


modeladmin_register(HarvestAdminGroup)
