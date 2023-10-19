from django.utils.translation import gettext as _

from article.tasks import article_source_to_article


def run(user_id, update):
    """
    Load the article from SourceArticle model to Article model.
    """
    if user_id:
        # load_openalex_article.apply_async(args=(int(user_id), bool(int(update))))
        # load_openalex_article(int(user_id), bool(int(update)))
        article_source_to_article(int(user_id), size=1000)
    else:
        print(_("Param user_id is required."))
