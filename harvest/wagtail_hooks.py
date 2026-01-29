from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet, SnippetViewSetGroup

from .models import HarvestedBooks, HarvestedPreprint, HarvestedSciELOData


class HarvestedPreprintViewSet(SnippetViewSet):
    model = HarvestedPreprint
    menu_label = "Preprint"
    icon = "doc-full"
    list_display = ("identifier", "harvest_status", "datestamp", "created")
    search_fields = ("identifier", "source_url")
    list_filter = ("harvest_status", "index_status")


class HarvestedSciELODataViewSet(SnippetViewSet):
    model = HarvestedSciELOData
    menu_label = "SciELO Data"
    icon = "doc-full"
    list_display = ("identifier", "harvest_status", "datestamp", "created")
    search_fields = ("identifier", "source_url")
    list_filter = ("harvest_status", "index_status", "type_data")


class HarvestedBooksViewSet(SnippetViewSet):
    model = HarvestedBooks
    menu_label = "Books"
    icon = "doc-full"
    list_display = ("identifier", "harvest_status", "datestamp", "created")
    search_fields = ("identifier", "source_url")
    list_filter = ("harvest_status", "index_status", "type_data")


class HarvestViewSetGroup(SnippetViewSetGroup):
    menu_label = "Harvest"
    menu_icon = "download"
    items = (
        HarvestedPreprintViewSet,
        HarvestedSciELODataViewSet,
        HarvestedBooksViewSet,
    )


register_snippet(HarvestViewSetGroup)
