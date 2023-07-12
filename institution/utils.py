from institution import models

from education_directory.models import EducationDirectory
from infrastructure_directory.models import InfrastructureDirectory
from policy_directory.models import PolicyDirectory
from scholarly_articles.models import Affiliations


def check_duplicate_institutions(inst):
    """
    This function return if there is duplicate instituins.

    Return a list with the reference to institution and the size of the duplications.
    """

    if inst.name and inst.acronym and inst.location and inst.institution_type:
        insts = models.Institution.objects.filter(
            name__iexact=inst.name,
            acronym__iexact=inst.acronym,
            location=inst.location,
            institution_type=inst.institution_type,
        )
    elif inst.name and inst.acronym and inst.location:
        insts = models.Institution.objects.filter(
            name__iexact=inst.name,
            acronym__iexact=inst.acronym,
            location=inst.location,
        )
    elif inst.name and inst.acronym:
        insts = models.Institution.objects.filter(
            name__iexact=inst.name,
            acronym__iexact=inst.acronym,
        )
    elif inst.name and inst.location:
        insts = models.Institution.objects.filter(
            name__iexact=inst.name,
            location=inst.location,
        )
    elif inst.name and inst.institution_type:
        insts = models.Institution.objects.filter(
            name__iexact=inst.name,
            institution_type=inst.institution_type,
        )
    elif inst.acronym and inst.location:
        insts = models.Institution.objects.filter(
            acronym__iexact=inst.acronym,
            location=inst.location,
        )
    elif inst.location and inst.institution_type:
        insts = models.Institution.objects.filter(
            location=inst.location,
            institution_type=inst.institution_type,
        )
    elif inst.acronym and inst.institution_type:
        insts = models.Institution.objects.filter(
            acronym__iexact=inst.acronym,
            institution_type=inst.institution_type,
        )
    elif inst.name and inst.institution_type:
        insts = models.Institution.objects.filter(
            name__iexact=inst.name,
            institution_type=inst.institution_type,
        )
    elif inst.name:
        insts = models.Institution.objects.filter(
            name__iexact=inst.name
        )

    if insts:
        qt = len(insts)
        if qt > 1:
            return insts


def reassignment_education_dir(casted_inst, dinsts):
    """
    This function receive a casted inst and a list of inst to search by Education Directory.

    This found education directory must be reassignment to the casted institution.

    Return a list of education reassigned.
    """

    educations_dir = None

    for inst in dinsts:
        educations_dir = EducationDirectory.objects.filter(institutions=inst)

        for education in educations_dir:
            # remove the duplicate instituion
            education.institutions.remove(inst)
            # add the casted instituiion
            education.institutions.add(casted_inst)
            education.save()

    return educations_dir


def reassignment_infra_dir(casted_inst, dinsts):
    """
    This function receive a casted inst and a list of inst to search by Infrastructure Directory.

    This found infrastructure directory must be reassignment to the casted intitution.

    Return a list of infrastructure reassigned.
    """

    infras_dir = None

    for inst in dinsts:
        infras_dir = InfrastructureDirectory.objects.filter(institutions=inst)

        for infra in infras_dir:
            # remove the duplicate instituion
            infra.institutions.remove(inst)
            # add the casted instituiion
            infra.institutions.add(casted_inst)
            infra.save()

    return infras_dir


def reassignment_policy_dir(casted_inst, dinsts):
    """
    This function receive a casted inst and a list of inst to search by Policy Directory.

    This found policy directory must be reassignment to the casted intitution.

    Return a list of policy reassigned.
    """

    polis_dir = None

    for inst in dinsts:
        polis_dir = PolicyDirectory.objects.filter(institutions=inst)

        for poli in polis_dir:
            # remove the duplicate instituion
            poli.institutions.remove(inst)
            # add the casted instituiion
            poli.institutions.add(casted_inst)
            poli.save()

    return polis_dir


def reassignment_affiliation(casted_inst, dinsts):
    """
    This function receive a casted inst and a list of inst to search by scholarly_articles.Affilications.

    This found affiliations must be reassignment to the casted intitution.

    Return a list of affiliations reassigned.
    """

    affs_dir = None

    for inst in dinsts:
        affs_dir = Affiliations.objects.filter(official=inst)

        for aff in affs_dir:
            # remove the duplicate instituion
            aff.institutions.remove(inst)
            # add the casted instituiion
            aff.institutions.add(casted_inst)
            aff.save()

    return affs_dir


def check_orphans_institutions():
    """
    This function return institutions that dont have associate with:

        * Education Directory
        * Infrastructure Directory
        * Policy Directory 
        * Scholarly Articles.Affiliations

    return a list of journals without articles associate.
    """
    orphans_inst = []

    for inst in models.Institution.objects.all():
        einst = EducationDirectory.objects.filter(institutions=inst)
        iinst = InfrastructureDirectory.objects.filter(institutions=inst)
        pinst = PolicyDirectory.objects.filter(institutions=inst)
        ainst = Affiliations.objects.filter(official=inst)

        if len(einst) == 0 and len(iinst) == 0 and len(pinst) == 0 and len(ainst) == 0:
            orphans_inst.append(models.Institution.objects.get(pk=inst.id))

    return orphans_inst