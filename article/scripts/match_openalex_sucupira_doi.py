
import re 
import logging

import pysolr
from django.conf import settings
from django.utils.translation import gettext as _

from article import models
from core.models import Source

solr = pysolr.Solr(
    settings.HAYSTACK_CONNECTIONS["default"]["URL"],
    timeout=settings.HAYSTACK_CONNECTIONS["default"]["SOLR_TIMEOUT"],
)

logger = logging.getLogger(__name__)

def run(year=2017):
    """
    This script search the articles by DOI from OpenAlex to Sucupira. 

    The data of DOI in Sucupira is something with just the ID, example: 

        10.1590/1980-5373-MR-2016-0983
        HTTP://DX.DOI.ORG/10.1590/1807-1929/AGRIAMBI.V22N4P249-254
        HTTPS://DOI.ORG/10.1080/09553002.2018.1492757
        10.1109/TNS.2018.2846668
        [DOI:10.1016/J.JLUMIN.2018.03.059]
        DOI: HTTP://DX.DOI.ORG/10.5007/1807-0221.2017V14N26P65
        DOI: HTTPS://DOI.ORG/10.5007/1518-2924.2017V22N50P114
    
    This search by 1518-2924.2017V22N50P114 AND source:openalex
    """

    source = Source.objects.get(name="SUCUPIRA")

    # Get all 
    articles = models.SourceArticle.objects.filter(year=year, source=source).exclude(doi__exact="")

    doi_pattern = r'\b10\.\d{4,9}/[-.;()/:\w]+'

    found = 0
    valid_doi = 0
    total = len(articles)

    logger.info("Article with DOI in %s for year(%s): %s" % (source, year, total))

    for article in articles:

        # clean doi
        cdoi = re.search(doi_pattern, article.doi)

        if cdoi:
            valid_doi += 1 
            cdoi = cdoi.group()

            q = "%s AND source:%s" % (cdoi, "OPENALEX")

            logger.info(q)

            r = solr.search(q)

            if r.docs:
                found += 1

    logger.info("Total of valid DOI: %s in Sucupira, total of found: %s in OpenAlex, porcent: %s" % (valid_doi, found, (found/33716) * 100)) 