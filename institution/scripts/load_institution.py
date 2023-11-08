from django.utils.translation import gettext as _

from institution.tasks import load_institution


def run(user_id, length=None, country=None):
    """
    Load the institution from OpenAlex to SourceInstitution model.

    About the OpenAlex API see: https://docs.openalex.org/

    Example: python manage.py runscript load_institution --script-args 1 100000000 BR
    """

    if user_id and length and country:
        load_institution.apply_async(args=(int(user_id), int(length), country))
    elif user_id and length:
        load_institution.apply_async(args=(int(user_id), int(length)))
    elif user_id:
        load_institution.apply_async(args=(int(user_id), ))
    else:
        print(_("Param user_id required."))
