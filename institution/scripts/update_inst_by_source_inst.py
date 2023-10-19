from django.utils.translation import gettext as _

from institution.models import Institution, SourceInstitution, InstitutionTranslateName

from institution import tasks

def run(*args):
    """
    This script update the Sources on Institution bind the translation name on SourceInstitution.

    Update the city of the found institutions.
    """

    user_id = args[0] if args else 1

    tasks.update_inst_by_source_inst(user_id)
        