import itertools
import logging
import re

import pysolr
from django.conf import settings
from django.utils.translation import gettext as _

from article import models
from indicator import indicator

solr = pysolr.Solr(
    settings.HAYSTACK_CONNECTIONS["default"]["URL"],
    timeout=settings.HAYSTACK_CONNECTIONS["default"]["SOLR_TIMEOUT"],
)

logger = logging.getLogger(__name__)


def run(graphic_text=0):
    """
    This will loop up to all itens on index and generate the graph.
    """

    # Quantidade de apc entre 2012 até 2023
    indicators = [
        {
            "filters": [],
            "title": "Institution X APC",
            "facet_by": "year",
            "context_by": ["institutions", "apc"],
            "default_filter": {"record_type": "article"},
            "range_filter": {"filter_name": "year", "range": {"start": 2012, "end": 2023}},
        },
        {
            "filters": [],
            "title": "Institution X License",
            "facet_by": "year",
            "context_by": ["institutions", "license"],
            "default_filter": {"record_type": "article"},
            "range_filter": {"filter_name": "year", "range": {"start": 2012, "end": 2023}},
        },
        {
            "filters": [],
            "title": "Institution X OpenAccess",
            "facet_by": "year",
            "context_by": ["institutions", "open_access_status"],
            "default_filter": {"record_type": "article"},
            "range_filter": {"filter_name": "year", "range": {"start": 2012, "end": 2023}},
        },
        {
            "filters": [],
            "title": "States X APC",
            "facet_by": "year",
            "context_by": ["states", "apc"],
            "default_filter": {"record_type": "article"},
            "range_filter": {"filter_name": "year", "range": {"start": 2012, "end": 2023}},
        },
        {
            "filters": [],
            "title": "States X License",
            "facet_by": "year",
            "context_by": ["states", "license"],
            "default_filter": {"record_type": "article"},
            "range_filter": {"filter_name": "year", "range": {"start": 2012, "end": 2023}},
        },
        {
            "filters": [],
            "title": "States X OpenAccess",
            "facet_by": "year",
            "context_by": ["states", "open_access_status"],
            "default_filter": {"record_type": "article"},
            "range_filter": {"filter_name": "year", "range": {"start": 2012, "end": 2023}},
        },
        {
            "filters": [],
            "title": "Thematic_level_0XAPC",
            "facet_by": "year",
            "context_by": ["thematic_level_0", "apc"],
            "default_filter": {"record_type": "article"},
            "range_filter": {"filter_name": "year", "range": {"start": 2012, "end": 2023}},
        },
        {
            "filters": [],
            "title": "Thematic_level_0 X OpenAccess",
            "facet_by": "year",
            "context_by": ["thematic_level_0", "open_access_status"],
            "default_filter": {"record_type": "article"},
            "range_filter": {"filter_name": "year", "range": {"start": 2012, "end": 2023}},
        },
    ]

    for ind in indicators:
        ind = indicator.Indicator(**ind)

    if graphic_text:
        serie_list = []
        for item in ind.generate():
            for serie_name_and_stack, data in item.items():

                if "-" in serie_name_and_stack:
                    stack = " ".join(serie_name_and_stack.split("-")[1:])
                else:
                    stack = serie_name_and_stack

                serie_list.append(
                    """{ name: '%s', type: 'bar', stack: '%s', emphasis: { focus: 'series' }, data: %s, label: { show: true } },"""
                    % (
                        serie_name_and_stack,
                        stack,
                        str(list(data.get("counts"))),
                    )
                )
                

        print("""option = {
                    title:{
                    show:true,
                    text: '%s',
                    textAlign:'auto',
                    },
                    tooltip: {
                    tooltip: {
                        trigger: 'axis'
                    },
                    },
                grid: {
                    left: '1',
                    right: '30',
                    bottom: '3',
                    containLabel: true
                },
                legend: {
                    type: 'scroll',
                    orient: 'vertical',
                    right: 0,
                    top: 20,
                    bottom: 20,
                },
                    xAxis: [
                    {
                        type: 'category',
                        data: ['2023', '2022', '2021', '2020', '2019', '2018', '2017', '2016', '2015', '2014','2013','2012']
                    }
                    ],
                    yAxis: [
                    {
                        type: 'value'
                    }
                    ],
                    series: [%s]
                };""" % (ind.title, "".join(serie_list)))
    else:
        print(ind.generate())
        
    # print(ind.get_ids())
    