from django.utils.translation import gettext as _

from article.tasks import match_contrib_aff_source_with_inst_MEC
from article import models
from institution.models import Institution

def run(user_id):
    """
    Match between affiliation.source and Institution[MEC]
    """
    if user_id:
        match_contrib_aff_source_with_inst_MEC(int(user_id))
    else:
        print(_("Param user_id is required."))
