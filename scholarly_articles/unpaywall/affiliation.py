from django.db.models import Q

from scholarly_articles.models import Affiliations
from usefulmodels.models import Country
from institution.models import Institution


def complete_affiliation_data():
    """
    Varre Institution e completa Afffiliations com official (MEC) e country
    com dados de países obtidos de bases auxiliares e da lista controlada
    de nomes de países
    É necessário seguir esta ordem de tentativas para completar os dados
    """
    for institution in Institution.objects.filter(source='MEC').iterator():
        for aff in Affiliations.objects.filter(
                official__isnull=True,
                name__icontains=institution.name).iterator():
            aff.official = institution
            aff.save()

    # first iteration to identify country by institution ROR
    for institution_ror in Institution.objects.filter(source="ROR").iterator():
        for aff in Affiliations.objects.filter(
                official__isnull=True,
                country__isnull=True,
                name__icontains=institution_ror.name,
                ).iterator():
            aff.country = institution_ror.location.country
            aff.save()

    for country in Country.objects.all():
        # second iteration to identify country by declared name
        for aff in Affiliations.objects.filter(
                Q(name__icontains=country.name_en) |
                Q(name__icontains=country.name_pt),
                country__isnull=True,
                official__isnull=True,
                ).iterator():
            aff.country = country
            aff.save()

        # third iteration to identify country by declared acronym with 3 char
        for aff in Affiliations.objects.filter(
                Q(name__contains=", "+country.acron3+", ") |
                Q(name__endswith=", "+country.acron3),
                country__isnull=True,
                official__isnull=True,
                ).iterator():
            aff.country = country
            aff.save()

        # fourth iteration to identify country by declared acronym with 2 char
        for aff in Affiliations.objects.filter(
                Q(name__contains=", "+country.acron2+", ") |
                Q(name__endswith=", "+country.acron2),
                country__isnull=True,
                official__isnull=True,
                ).iterator():
            aff.country = country
            aff.save()
