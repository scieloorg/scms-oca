import csv
import datetime
import json
import logging
import math
import os
from collections import OrderedDict

import pysolr
from django.conf import settings
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.template import loader
from django.urls import reverse

from indicator.models import Indicator
from search.graphic_data import GraphicData
from indicator import indicator
from core.utils import utils
from . import choices

from pyalex import Works

solr = pysolr.Solr(
    settings.HAYSTACK_CONNECTIONS["default"]["URL"],
    timeout=settings.HAYSTACK_CONNECTIONS["default"]["SOLR_TIMEOUT"],
)


def search(request):
    fqs = []
    filters = {}
    search_query = request.GET.get("q", None)
    search_field = request.GET.get("search-field", None)
    fqfilters = request.GET.get("filters", None)
    facet_name = request.GET.get("more_facet_name", None)
    facet_count = request.GET.get("more_facet_count", None)
    sort_by = request.GET.get("selectSortKey", "geo_priority asc")

    # default fqs
    dfqs = True if request.GET.get("dfqs", "true").lower() == "true" else False

    if search_query == "" or not search_query:
        search_query = "*:*"

    if search_field:
        search_query = search_field

    # Page
    try:
        page = abs(int(request.GET.get("page", 1)))
    except (TypeError, ValueError):
        return Http404("Not a valid number for page.")

    rows = int(request.GET.get("itensPage", settings.SEARCH_PAGINATION_ITEMS_PER_PAGE))

    start_offset = (page - 1) * rows

    filters["start"] = start_offset
    filters["rows"] = rows

    if facet_name and facet_count:
        filters["f." + facet_name + ".facet.limit"] = facet_count

    if fqfilters:
        fqs = fqfilters.split("|")

    fqs = ['%s:"%s"' % (fq.split(":")[0], fq.split(":")[1]) for fq in fqs]

    if dfqs:
        fqs.append('record_status:"PUBLISHED"')

    # Adiciona o Solr na pesquisa
    search_results = solr.search(search_query, fq=fqs, sort=sort_by, **filters)

    if request.GET.get("raw"):
        return JsonResponse(search_results.raw_response, safe=False)

    # Cria um dicionário ordenado dos facets considerando a lista settings.SEARCH_FACET_LIST
    facets = search_results.facets["facet_fields"]
    ordered_facets = OrderedDict()

    for facet in settings.SEARCH_FACET_LIST:
        ordered_facets[facet] = facets.get(facet, "")

    wt = request.GET.get("wt")
    if wt == "csv":
        filename = "%s_%s.csv" % (
            "download_csv_",
            datetime.datetime.today().strftime("%d_%m_%Y"),
        )

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="%s"' % (filename)

        t = loader.get_template("csv_template.txt")
        c = {"search_results": search_results}
        response.write(t.render(c))
        return response

    total_pages = int(math.ceil(float(search_results.hits) / rows))

    return render(
        request,
        "search.html",
        {
            "search_query": "" if search_query == "*:*" else search_query,
            "search_results": search_results,
            "facets": ordered_facets,
            "page": page,
            "fqfilters": fqfilters if fqfilters else "",
            "start_offset": start_offset,
            "itensPage": rows,
            "wt": wt if wt else "HTML",
            "settings": settings,
            "total_pages": total_pages,
            "selectSortKey": sort_by,
        },
    )


def _get_indicator(request, indicator_slug):
    # check if the slug is not a database id else redirect to slug url format
    try:
        return Indicator.get(indicator_slug, record_status="PUBLISHED")
    except Indicator.DoesNotExist:
        raise Http404("Indicator does not exist")


def indicator_detail(request, indicator_slug):
    indicator = _get_indicator(request, indicator_slug)
    if indicator.slug != indicator_slug:
        return redirect(
            reverse(
                "search:indicator_detail", kwargs={"indicator_slug": indicator.slug}
            ),
            permanent=True,
        )

    summarized = json.loads(indicator.summarized)

    return render(
        request,
        "indicator/indicator_detail.html",
        {
            "object": indicator,
            "chart_keys": summarized.get("keys"),
            "chart_series": summarized.get("series"),
        },
    )


def indicator_summarized(request, indicator_slug):
    indicator = _get_indicator(request, indicator_slug)

    filename, ext = os.path.splitext(os.path.basename(indicator.raw_data.name))
    filename = filename + ".csv"

    response = HttpResponse(
        content_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="%s"' % filename},
    )

    for item in indicator.summarized["items"]:
        fieldnames = indicator.summarized["table_header"]
        break
    logging.info(indicator.summarized["table_header"])

    writer = csv.DictWriter(response, fieldnames=fieldnames)

    writer.writeheader()
    for item in indicator.summarized["items"]:
        try:
            writer.writerow(item)
        except:
            logging.info(item)
    return response


def indicator_raw_data(request, indicator_slug):
    indicator = _get_indicator(request, indicator_slug)

    filename = os.path.basename(indicator.raw_data.name)
    response = HttpResponse(indicator.raw_data, content_type="application/zip")
    response["Content-Disposition"] = "attachment; filename=%s" % filename
    return response


def graph(request):

    search_results = solr.search("*:*")

    return render(
        request,
        "graph/graph.html",
        {"facets": search_results.facets["facet_fields"]},
    )


def graph_json(request):
    """
    This view function return the data of a Indicator class.

    Params:
        filters: Param of query this param must be in the ``filters`` on the dictionary
        title: Param title to the graph this is generate automatic if not send.
               Example of automatic title: Universo: Mundo; Anos: 2014-2023; Número de documentos por tipo
        facet_by: Indicates by which data we will group the result
        description: The description of the graph
               Gerado automaticamente usando dados coletados do OpenALex no período de 2014 até 2023"
        context_by: [] by now this is a empty list
        default_filter: This is the default items add to the list of items
        range_start: The star of the range
        range_end: The end of the range
    Return:

    """

    ind = {
        "filters": [{"year": "*"}],
        "title": "",
        "facet_by": "year",
        "description": "Gerado automaticamente usando dados coletados do OpenALex no período de 2014 até 2023",
        "context_by": [],
        "default_filter": {
        },
        "range_filter": {
            "filter_name": "year",
            "range": {"start": 2014, "end": 2023},
        },
    }

    filters = request.GET.get("filters", None)
    if filters:
        ind["filters"] = utils.parse_string_to_dicts(filters)

    title = request.GET.get("title", None)
    if title:
        ind["title"] = title

    facet_by = request.GET.get("facet_by", None)
    if facet_by:
        ind["facet_by"] = facet_by

    description = request.GET.get("description", None)
    if description:
        ind["description"] = description

    context_by = request.GET.get("context_by", None)
    if context_by:
        ind["context_by"] = context_by.split(",")
        # Se tem contexto deve ser removido o filtro padrão {"year": "*"}
        ind["filters"] = []

    default_filter = request.GET.get("default_filter", None)
    if default_filter:
        ind["default_filter"] = utils.parse_string_to_dicts(
            default_filter, ret_type="dict"
        )

    start = request.GET.get("start", None)
    if start:
        ind["range_filter"]["range"]["start"] = int(start)

    end = request.GET.get("end", None)
    if end:
        ind["range_filter"]["range"]["end"] = int(end)

    if not (start or end):
        ind["range_filter"] = None

    graph_type = request.GET.get("graph_type", "bar")
    graph_label = request.GET.get("graph_label", None)

    graph_legend_orient = request.GET.get("graph_legend_orient", "horizontal")
    graph_legend_right = request.GET.get("graph_legend_right_margin", "auto")
    graph_legend_right_margin = request.GET.get("graph_legend_right_margin", "auto")
    graph_legend_left = request.GET.get("graph_legend_left", "auto")
    graph_legend_left_margin = request.GET.get("graph_legend_left_margin", "auto")
    graph_legend_top = request.GET.get("graph_legend_top", "bottom")

    logging.info("Indicator dict: %s" % ind)

    w_total = 0

    if request.GET.get("percent", None):
        for year in range(int(start), int(end) + 1):
            print(year)
            result, meta = (
                    Works()
                    .filter(publication_year=year)
                    .get(return_meta=True)
                )
        
            # world count 
            w_total += int(meta.get("count"))

    title = request.GET.get("title", None)

    if not title:

        title = "Evolução da Produção Científica por Ano"

        if filters != "*:*":
            title += ": Um Panorama por %s" % (
                " e ".join(
                    [choices.translates.get(t) for t in ind.get("context_by")] +
                    [choices.translates.get(t) for t in ind["default_filter"].keys()]
                )
            )

    ind = indicator.Indicator(**ind)

    serie = {}
    serie_list = []
    filter_list = None

    for item in ind.generate():

        for serie_name_and_stack, data in item.items():
            if data:
                if "-" in serie_name_and_stack:
                    stack = " ".join(serie_name_and_stack.split("-")[1:])
                else:
                    stack = serie_name_and_stack

                serie_list.append(
                    {
                        "name": (
                            choices.translates.get(ind.facet_by, ind.facet_by)
                            if serie_name_and_stack == "*"
                            else choices.translates.get(
                                serie_name_and_stack, serie_name_and_stack
                            )
                        ),
                        "type": graph_type,
                        "stack": ind.facet_by if stack == "*" else stack,
                        "emphasis": {"focus": "series"},
                        "data": list(data.get("counts")),
                        "label": {"show": graph_label},
                    }
                )
                filter_list = data.get("filters")

        if ind.range_filter:
            serie = {
                "keys": [
                    key
                    for key in range(
                        ind.range_filter.get("range").get("start"),
                        ind.range_filter.get("range").get("end") + 1,
                    )
                ],
                "series": serie_list,
            }
        else:
            serie = {
                "keys": data.get("items"),
                "series": serie_list,
            }

    return JsonResponse(
        {
            "graph_options": {
                # Evolução da Produção Científica por ano: Um Panorama por Ano e Área Temática
                "title": title,
                "percent": request.GET.get("percent", None),
                "graph_legend_orient": graph_legend_orient,
                "graph_legend_right": graph_legend_right,
                "graph_legend_right_margin": graph_legend_right_margin,
                "graph_legend_left": graph_legend_left,
                "graph_legend_left_margin": graph_legend_left_margin,
                "graph_legend_top": graph_legend_top,
            },
            "data": serie,
            "filters": filter_list,
            "oa_data": {
                "world_count": w_total or 0,
            }
        }
    )
