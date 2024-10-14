from django.utils.translation import gettext as _

from journal.tasks import load_journal_openalex

from journal.models import SourceJournal


def run(user_id, country="BR", delete=0, length=None):
    """
    Load the journal from OpenAlex to SourceJournal model.

    About the OpenAlex API see: https://docs.openalex.org/
    """

    if int(delete):
        SourceJournal.objects.all().delete()

    if user_id and country and length:
        load_journal_openalex.apply_async(args=(int(user_id), str(country), int(length)))
    elif user_id and country:
        load_journal_openalex.apply_async(args=(int(user_id), str(country)))
    else:
        print(_("Param user_id is required."))
