from wagtail.contrib.modeladmin.options import (
    ModelAdmin,
    ModelAdminGroup,
    modeladmin_register,
)
from .models import HarvestedPreprint, HarvestedSciELOData, HarvestedBooks


class HarvestedPreprintModelAdmin(ModelAdmin):
    model = HarvestedPreprint
    menu_label = "Harvest Preprint"
    list_display = ("identifier", "harvest_status", "datestamp", "created")
    search_fields = ("identifier", "source_url")
    list_filter = ("harvest_status", "index_status")


modeladmin_register(HarvestedPreprintModelAdmin)


class HarvestedSciELODataModelAdmin(ModelAdmin):
    model = HarvestedSciELOData
    menu_label = "Harvest SciELO Data"
    list_display = ("identifier", "harvest_status", "datestamp", "created")
    search_fields = ("identifier", "source_url")
    list_filter = ("harvest_status", "index_status", "type_data")


modeladmin_register(HarvestedSciELODataModelAdmin)


class HarvestedBooksModelAdmin(ModelAdmin):
    model = HarvestedBooks
    menu_label = "Harvest Books"
    list_display = ("identifier", "harvest_status", "datestamp", "created")
    search_fields = ("identifier", "source_url")
    list_filter = ("harvest_status", "index_status", "type_data")


modeladmin_register(HarvestedBooksModelAdmin)
