from scholarly_articles import models as article_models
from institution import models as institution_models


def load_official_name():
    for official in institution_models.Institution.objects.filter(source='MEC').iterator():
        for aff in article_models.Affiliations.objects.filter(name__icontains=official.name).iterator():
             aff.official = official
             aff.save()


def run():
    load_official_name()