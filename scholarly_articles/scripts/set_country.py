from django.db.models import Q

from scholarly_articles import models
from usefulmodels.models import Country


def run():
    for country in Country.objects.all():
        for aff in models.Affiliations.objects.filter(
                Q(name__icontains=country.name_en) | Q(name__icontains=country.name_pt),
                  country__isnull=True, official__isnull=True).iterator():
            aff.country = country
            aff.save()
