import logging

from django.db.models import Q, Count
from django.contrib.auth import get_user_model

from scholarly_articles.models import Affiliations
from usefulmodels.models import Country
from institution.models import Institution
from location.models import Location


User = get_user_model()


def display_stats(text):
    logging.info(text)

    q1 = Affiliations.objects.filter(official__isnull=True).count()
    logging.info(f"official__isnull: {q1}")

    q2 = Affiliations.objects.filter(country__isnull=True).count()
    logging.info(f"country__isnull: {q2}")

    return q1, q2


def delete_aff_country_and_official():
    for aff in Affiliations.objects.filter(
            Q(country__isnull=False)
            | Q(official__isnull=False)).iterator():
        aff.country = None
        aff.official = None
        logging.info(f"delete country and official {aff.name}")
        aff.save()


def set_official_searching_by_mec_institution_name(force_update=None):
    """
    Varre Institution (MEC) e completa Affiliations
    """

    for institution in Institution.objects.filter(
        source="MEC",
        location__country__acron2__isnull=False,
        location__country__name_pt__isnull=False,
        location__country__name_en__isnull=False,
    ).iterator():
        logging.info(f"{institution.name}")
        if not institution.location.country.name_en:
            continue
        if not institution.location.country.name_pt:
            continue

        params = {}
        params['name__icontains'] = institution.name
        if not force_update:
            params['official__isnull'] = True

        for aff in Affiliations.objects.filter(**params).iterator():
            aff.official = institution
            aff.country = institution.location.country
            aff.save()
            logging.info(f"{aff.name} -> {institution.name}")
    return display_stats("MEC name")


def set_country_searching_by_capital_and_country():
    for country in Country.objects.filter(
        Q(name_pt__isnull=False) | Q(name_en__isnull=False),
        acron2__isnull=False,
        acron3__isnull=False,
        capital__isnull=False,
    ).iterator():
        # third iteration to identify country by declared acronym with 3 char
        if not country.acron2 or country.acron2 == "ALL":
            continue
        if not country.capital:
            continue
        if not country.name_en:
            continue
        if not country.name_pt:
            continue
        for aff in Affiliations.objects.filter(
            Q(name__icontains=country.capital) & Q(name__icontains=country.name_en)
            | Q(name__icontains=country.capital) & Q(name__icontains=country.name_pt),
            official__isnull=True,
            country__isnull=True,
        ).iterator():
            aff.country = country
            aff.save()
            logging.info(f"{country.capital}")
            logging.info(f"{aff.name} -> {aff.country.acron2} - Country code / capital")
    return display_stats("Country code / capital")


def set_country_searching_by_country_state_city_():
    for institution in Institution.objects.filter(
        source="ROR",
        location__country__acron2__isnull=False,
        location__country__name_pt__isnull=False,
        location__country__name_en__isnull=False,
        location__city__name__isnull=False,
        location__state__name__isnull=False,
    ).iterator():
        logging.info(institution.name)
        country_name_pt = institution.location.country.name_pt
        country_name_en = institution.location.country.name_en
        city = institution.location.city.name
        state = institution.location.state.name

        q = []
        if state and city:
            q.append(Q(name__icontains=state) & Q(name__icontains=city))
        if city and country_name_en:
            q.append(Q(name__icontains=city) & Q(name__icontains=country_name_en))
        if city and country_name_pt:
            q.append(Q(name__icontains=city) & Q(name__icontains=country_name_pt))
        if state and country_name_en:
            q.append(Q(name__icontains=state) & Q(name__icontains=country_name_en))
        if state and country_name_pt:
            q.append(Q(name__icontains=state) & Q(name__icontains=country_name_pt))
        if not q:
            continue

        qs = q[0]
        for item in q[1:]:
            qs |= item

        for aff in Affiliations.objects.filter(
            qs,
            official__isnull=True,
            country__isnull=True,
        ).iterator():
            aff.country = institution.location.country
            aff.save()
            logging.info(f"|{country_name_en}|{country_name_pt}|{city}|{state}|")
            logging.info(f"{aff.name} -> {aff.country.acron2} - city / state / country")

    return display_stats("city / state / country")


def set_country_searching_by_country_state_city():
    for item in Location.objects.filter(
            Q(state__isnull=False) | Q(city__isnull=False),
            country__acron2__isnull=False,
            country__name_pt__isnull=False,
            country__name_en__isnull=False,
        ).values(
            'city__name',
            'state__name',
            'state__acronym',
            'country__acron2',
            'country__name_pt',
            'country__name_en',
        ).annotate(
            count=Count("id")
        ).iterator():
        city_name = item["city__name"]
        state_name = item["state__name"]
        state_acronym = item["state__acronym"]
        country_acron2 = item["country__acron2"]
        country_name_pt = item["country__name_pt"]
        country_name_en = item["country__name_en"]

        if city_name == "ALL" or state_name == "ALL":
            continue
        if city_name == "virtual" or state_name == "virtual":
            continue
        q = []
        if state_name and city_name:
            q.append(Q(name__icontains=state_name) & Q(name__icontains=city_name))
        if city_name and country_name_en:
            q.append(Q(name__icontains=city_name) & Q(name__icontains=country_name_en))
        if city_name and country_name_pt:
            q.append(Q(name__icontains=city_name) & Q(name__icontains=country_name_pt))
        if state_name and country_name_en:
            q.append(Q(name__icontains=state_name) & Q(name__icontains=country_name_en))
        if state_name and country_name_pt:
            q.append(Q(name__icontains=state_name) & Q(name__icontains=country_name_pt))
        if not q:
            continue

        country = Country.objects.filter(
            capital__isnull=False,
            acron2=country_acron2,
            name_pt=country_name_pt,
            name_en=country_name_en,
        ).first()
        logging.info(f"|{country_name_en}|{country_name_pt}|{city_name}|{state_name}|")

        qs = q[0]
        for item in q[1:]:
            qs |= item

        for aff in Affiliations.objects.filter(
            qs,
            official__isnull=True,
            country__isnull=True,
        ).iterator():
            aff.country = country
            aff.save()
            logging.info(f"|{country_name_en}|{country_name_pt}|{city_name}|{state_name}|")
            logging.info(f"{aff.name} -> {aff.country.acron2} - city / state / country")

    return display_stats("city / state / country")


def set_country_searching_by_mec_acronym():
    for institution in Institution.objects.filter(
        source="MEC",
        location__country__acron2__isnull=False,
        location__country__name_pt__isnull=False,
        location__country__name_en__isnull=False,
        acronym__isnull=False,
    ).iterator():
        logging.info(institution.name)
        acronym = institution.acronym

        if not acronym:
            continue

        for aff in Affiliations.objects.filter(
            name__contains=acronym,
            official__isnull=True,
            country__isnull=True,
        ).iterator():
            aff.official = institution
            aff.country = institution.location.country
            aff.save()
            logging.info(f"|{acronym}|{institution.name}|")
            logging.info(f"{aff.name} -> {aff.country.acron2} - MEC acron")

    return display_stats("MEC acron")


def complete_affiliation_data():
    """
    Varre Institution e completa Afffiliations com official (MEC) e country
    com dados de países obtidos de bases auxiliares e da lista controlada
    de nomes de países
    É necessário seguir esta ordem de tentativas para completar os dados
    """
    q1, q2 = display_stats("Inicio")
    if q1 == q2 == 0:
        return

    # set_official_searching_by_mec_institution_name()

    # set_country_searching_by_capital_and_country()

    set_country_searching_by_country_state_city()
    set_country_searching_by_mec_acronym()
