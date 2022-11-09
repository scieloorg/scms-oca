from django.db.models import Q

from scholarly_articles import models
from usefulmodels.models import Country
from institution.models import Institution


def run():
    #first iteration to identify country by institution ROR
    for institution_ror in Institution.objects.filter(source="ROR").iterator():
        for aff in models.Affiliations.objects.filter(name__icontains=institution_ror.name,
                                                      country__isnull=True).iterator():
            aff.country = institution_ror.location.country
            aff.save()

    for country in Country.objects.all():
        #second iteration to identify country by declared name
        for aff in models.Affiliations.objects.filter(
                Q(name__icontains=country.name_en) | Q(name__icontains=country.name_pt),
                  country__isnull=True, official__isnull=True).iterator():
            aff.country = country
            aff.save()

        #third iteration to identify country by declared acronym with 3 char
        for aff in models.Affiliations.objects.filter(
                Q(name__contains=", "+country.acron3+", ") | Q(name__endswith=", "+country.acron3),
                country__isnull=True,
                official__isnull=True).iterator():
            aff.country = country
            aff.save()

        #fourth iteration to identify country by declared acronym with 2 char
        for aff in models.Affiliations.objects.filter(
                Q(name__contains=", " + country.acron2 + ", ") | Q(name__endswith=", " + country.acron2),
                country__isnull=True,
                official__isnull=True).iterator():
            aff.country = country
            aff.save()
