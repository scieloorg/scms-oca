
import re 
import logging

import pysolr
import json
from django.conf import settings
from django.utils.translation import gettext as _

from article import models
from core.models import Source


logger = logging.getLogger(__name__)

def run(source_name="OPENALEX"):

    source = Source.objects.get(name=source_name)
    for article in models.SourceArticle.objects.filter(source=source):
        print(article.raw.get("title"))
        print(len(article.raw.get("title")))
        if len(article.raw.get("title")) > 255:
            import pdb; pdb.set_trace()