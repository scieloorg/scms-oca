import csv
import datetime
import math
import os
from collections import OrderedDict

import pysolr
from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse
from django.db.models import Q
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import render
from django.template import loader

from core.utils import utils
from indicator import controller as indicator_controller
from indicator.models import Indicator

from . import controller

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

    fqs.append('record_status:"PUBLISHED"')

    # Adiciona o Solr na pesquisa
    search_results = solr.search(search_query, fq=fqs, sort=sort_by, **filters)

    # Cria um dicionário ordenado dos facets considerando a lista settings.SEARCH_FACET_LIST
    facets = search_results.facets["facet_fields"]
    ordered_facets = OrderedDict()

    for facet in settings.SEARCH_FACET_LIST:
        ordered_facets[facet] = facets.get(facet, "")

    if request.GET.get("raw"):
        return JsonResponse(search_results.raw_response, safe=False)

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


def indicator_detail(request, indicator_slug):
    # check if the slug is not a database id else redirect to slug url format
    if not utils.is_int(indicator_slug):
        try:
            indicator = Indicator.objects.get(
                Q(slug=indicator_slug) | Q(code=indicator_slug),
                record_status="PUBLISHED",
            )
        except Indicator.DoesNotExist:
            raise Http404("Indicator does not exist")

        indicator.latest = indicator_controller.get_latest_version(indicator.code).id
        parameters = controller.indicator_detail(request, indicator)
        return render(
            request,
            "indicator/indicator_detail.html",
            parameters or {"object": indicator},
        )
    else:
        try:
            indicator = Indicator.objects.get(
                id=indicator_slug, record_status="PUBLISHED"
            )
        except Indicator.DoesNotExist:
            raise Http404("Indicator does not exist")

        return redirect(
            reverse(
                "search:indicator_detail", kwargs={"indicator_slug": indicator.slug}
            ),
            permanent=True,
        )


def indicator_summarized(request, indicator_slug):
    # check if the slug is not a database id else redirect to slug url format
    if not utils.is_int(indicator_slug):
        try:
            indicator = Indicator.objects.get(
                Q(slug=indicator_slug) | Q(code=indicator_slug),
                record_status="PUBLISHED",
            )
        except Indicator.DoesNotExist:
            raise Http404("Indicator does not exist")

        filename, ext = os.path.splitext(os.path.basename(indicator.raw_data.name))
        filename = filename + ".csv"

        response = HttpResponse(
            content_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="%s"' % filename},
        )

        for item in indicator.summarized["items"]:
            fieldnames = item.keys()
            break

        writer = csv.DictWriter(response, fieldnames=fieldnames)

        writer.writeheader()
        for item in indicator.summarized["items"]:
            writer.writerow(item)
        return response
    else:
        try:
            indicator = Indicator.objects.get(
                id=indicator_slug, record_status="PUBLISHED"
            )
        except Indicator.DoesNotExist:
            raise Http404("Indicator does not exist")
        
        return redirect(
            reverse(
                "search:indicator_summarized", kwargs={"indicator_slug": indicator.slug}
            ),
            permanent=True,
        )


def indicator_raw_data(request, indicator_slug):
    # check if the slug is not a database id else redirect to slug url format
    if not utils.is_int(indicator_slug):
        try:
            indicator = Indicator.objects.get(
                Q(slug=indicator_slug) | Q(code=indicator_slug),
                record_status="PUBLISHED",
            )
        except Indicator.DoesNotExist:
            raise Http404("Indicator does not exist")

        filename = os.path.basename(indicator.raw_data.name)
        response = HttpResponse(indicator.raw_data, content_type="application/zip")
        response["Content-Disposition"] = "attachment; filename=%s" % filename
        return response
    else:
        try:
            indicator = Indicator.objects.get(
                id=indicator_slug, record_status="PUBLISHED"
            )
        except Indicator.DoesNotExist:
            raise Http404("Indicator does not exist")

        return redirect(
            reverse(
                "search:indicator_raw_data", kwargs={"indicator_slug": indicator.slug}
            ),
            permanent=True,
        )
