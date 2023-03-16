import os
from tempfile import TemporaryDirectory
from zipfile import ZipFile
import json
import shutil

from django.conf import settings
from django.db.models import Count

from institution.models import Institution
from scholarly_articles.models import Affiliations


def affiliations_numbers():
    stats = {}
    stats["institution__total"] = Institution.objects.count()
    inst__country = Institution.objects.filter(location__country__isnull=False)
    inst__state = Institution.objects.filter(location__state__isnull=False)
    inst__city = Institution.objects.filter(location__city__isnull=False)
    inst__country__BR = Institution.objects.filter(location__country__acron2="BR")
    stats["institution__city"] = inst__city.count()
    stats["institution__state"] = inst__state.count()
    stats["institution__country"] = inst__country.count()
    stats["institution__country__BR"] = inst__country__BR.count()
    stats["institution__MEC"] = Institution.objects.filter(source="MEC").count()

    stats["aff__total"] = Affiliations.objects.count()
    official = Affiliations.objects.filter(
        official__isnull=False,
    )
    official__country = official.filter(official__location__country__isnull=False)
    official__state = official.filter(official__location__state__isnull=False)
    official__city = official.filter(official__location__city__isnull=False)
    official__country__BR = official.filter(official__location__country__acron2="BR")

    stats["aff__official"] = official.count()
    stats["aff__official__city"] = official__city.count()
    stats["aff__official__state"] = official__state.count()
    stats["aff__official__country"] = official__country.count()
    stats["aff__official__country__BR"] = official__country__BR.count()
    stats["aff__country"] = Affiliations.objects.filter(
        country__isnull=False,
    ).count()
    stats["aff__country__BR"] = Affiliations.objects.filter(
        country__acron2="BR",
    ).count()
    stats["aff sem país e sem official"] = Affiliations.objects.filter(
        country__isnull=True,
        official__isnull=True,
    ).count()
    return stats


def generate_unmatched_affilition_countries_report():
    filename = "unmatched_affilition_countries"
    with TemporaryDirectory() as tmpdirname:
        temp_zip_file_path = os.path.join(tmpdirname, filename + ".zip")
        file_path = os.path.join(settings.MEDIA_ROOT, filename + ".zip")
        with ZipFile(temp_zip_file_path, "w") as zf:
            zf.writestr(file_path + ".jsonl", "".join(unmatched_affilition_countries()))
        print(file_path)
        shutil.move(temp_zip_file_path, file_path)


def unmatched_affilition_countries():
    for aff in (
        Affiliations.objects.filter(
            official__isnull=True,
            country__isnull=True,
        )
        .values("name")
        .annotate(count=Count("id"))
        .order_by("-count")
        .iterator()
    ):
        yield f"{json.dumps(aff)}\n"


def run():
    for k, v in affiliations_numbers().items():
        print(f"{k}\t{v}")

    generate_unmatched_affilition_countries_report()
