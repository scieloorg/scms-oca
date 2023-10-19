from django.utils.translation import gettext as _

from article.tasks import load_openalex


def run(user_id, date=2012, length=None):
    """
    Load the article from OpenAlex to SourceArticle model.

    About the OpenAlex API see: https://docs.openalex.org/
    """

    if user_id and date and length:
        load_openalex.apply_async(args=(int(user_id), int(date), int(length)))
    elif user_id and date :
        load_openalex.apply_async(args=(int(user_id), int(date)))
    else:
        print(_("Param user_id and date is required."))
