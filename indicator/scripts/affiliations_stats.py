from institution.models import Institution
from scholarly_articles.models import Affiliations


def affiliations_numbers():
    stats = {}
    stats['institution__total'] = Institution.objects.count()
    inst__country = Institution.objects.filter(
        location__country__isnull=False)
    inst__state = Institution.objects.filter(
        location__state__isnull=False)
    inst__city = Institution.objects.filter(
        location__city__isnull=False)
    inst__country__BR = Institution.objects.filter(
        location__country__acron2='BR')
    stats['institution__city'] = inst__city.count()
    stats['institution__state'] = inst__state.count()
    stats['institution__country'] = inst__country.count()
    stats['institution__country__BR'] = inst__country__BR.count()

    stats['aff__total'] = Affiliations.objects.count()
    official = Affiliations.objects.filter(
        official__isnull=False,
    )
    official__country = official.filter(
        official__location__country__isnull=False)
    official__state = official.filter(
        official__location__state__isnull=False)
    official__city = official.filter(
        official__location__city__isnull=False)
    official__country__BR = official.filter(
        official__location__country__acron2='BR')

    stats['aff__official'] = official.count()
    stats['aff__official__city'] = official__city.count()
    stats['aff__official__state'] = official__state.count()
    stats['aff__official__country'] = official__country.count()
    stats['aff__official__country__BR'] = official__country__BR.count()
    stats['aff__country'] = Affiliations.objects.filter(
            country__isnull=False,
        ).count()
    stats['aff__country__BR'] = Affiliations.objects.filter(
            country__acron2='BR',
        ).count()
    return {
        "items": [
            {"name": k, "count": v}
            for k, v in stats.items()
        ]
    }


def run():
    print(affiliations_numbers())
