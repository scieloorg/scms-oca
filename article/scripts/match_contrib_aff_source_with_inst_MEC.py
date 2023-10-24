from django.utils.translation import gettext as _

from article.tasks import match_contrib_aff_source_with_inst_MEC

def run(user_id):
    """
    Match between affiliation.source and Institution[MEC]
    """
    if user_id:
        match_contrib_aff_source_with_inst_MEC(int(user_id))
    else:
        print(_("Param user_id is required."))
