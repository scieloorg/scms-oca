from django.utils.translation import gettext as _

from article.tasks import match_contrib_inst_aff


def run(user_id):
    """
    contributor looking for contributor.institutions and find the affiliation
    """
    if user_id:
        match_contrib_inst_aff(int(user_id))
    else:
        print(_("Param user_id is required."))
