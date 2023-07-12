import csv
import logging
import os

from django.contrib.auth import get_user_model
from django.utils.translation import gettext as _

from config import celery_app
from institution import models, utils
from institution.scripts import bulk_institution

User = get_user_model()

logger = logging.getLogger(__name__)

@celery_app.task()
def load_official_institution(user_id):
    """
    Load the data from a CSV file.

    Sync or Async function

    Param user: The user id passed by kwargs on tasks.kwargs
    """
    user = User.objects.get(id=user_id)

    for item in [["mec", ";", "MEC"], ["ror", ",", "ROR"]]:
        with open(
            os.path.dirname(os.path.realpath(__file__))
            + f"/fixtures/institutions_{item[0]}.csv",
            "r",
        ) as csvfile:
            data = csv.DictReader(csvfile, delimiter=item[1])

            for line, row in enumerate(data):
                bulk_institution.load_official_institution(
                    creator=user, row=row, line=line, source=item[2]
                )


@celery_app.task(name=_("Sanitize by institutions"))
def sanitize_institutions(user_id):
    """
    This task go to all institutions and check if has duplicate.

    The models with the instituion as reference are: 

        * Education Directory
        * Infrastructure Directory
        * Policy Directory 
        * Scholarly Articles.Affiliations
    """
    for inst in models.Institution.objects.all():
        dinsts = utils.check_duplicate_institutions(inst)

        if dinsts:
            logger.info(
                "Duplicate institutions %s, size: %s" % (inst, len(dinsts))
            )

            casted_inst = None

            for i in dinsts:
                if i.name and i.acronym and i.location and i.institution_type:
                    casted_inst = i
                    break
                elif i.name and i.acronym and i.location:
                    casted_inst = i
                    break
                elif i.name and i.acronym:
                    casted_inst = i
                elif i.name:
                    casted_inst = i

                logger.info("Casted institution: %s" % casted_inst)

                logger.info("Reassigned Education Directory: %s" % utils.reassignment_education_dir(casted_inst, dinsts))
                logger.info("Reassigned Insfrastructure Directory: %s" % utils.reassignment_infra_dir(casted_inst, dinsts))
                logger.info("Reassigned Policy Directory: %s" % utils.reassignment_policy_dir(casted_inst, dinsts))
                logger.info("Reassigned Affiliation: %s" % utils.reassignment_affiliation(casted_inst, dinsts))


@celery_app.task(name=_("Remove institutions without any associated"))
def remove_orphans_institutions(user_id):
    """
    This task remove all orphans institutions.
    """
    logger.info("Checking for orphans institutions....")

    insts = utils.check_orphans_institutions()

    removed = [inst.delete() for inst in insts]

    logger.info("Reassigned institutions: %s" % removed)