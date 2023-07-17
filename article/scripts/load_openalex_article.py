from django.utils.translation import gettext as _

from article.tasks import load_openalex_article


def run(user_id, update):
    """
    Load the article from SourceArticle model to Article model.
    """
    if user_id:
        load_openalex_article.apply_async(args=(int(user_id), bool(int(update))))
    else:
        print(_("Param user_id is required."))
