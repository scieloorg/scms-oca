from scholarly_articles import models as article_models
from institution import models as institution_models


def run():
    for official in institution_models.Institution.objects.filter(source='MEC').iterator():
        for aff in article_models.Affiliations.objects.filter(name__upper__contains=official.upper()).iterator():
             aff.official = official
             aff.save()