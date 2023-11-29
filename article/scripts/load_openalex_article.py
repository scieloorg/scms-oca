from django.utils.translation import gettext as _

from article.tasks import article_source_to_article


def run(user_id, update, year):
    """
    Load the article from SourceArticle model to Article model.
    """
    if user_id:
        # https://openalex.org/I17974374
        # https://openalex.org/I16655442
        # https://openalex.org/I179964525
        article_source_to_article(int(user_id), year=str(year))
        # article_source_to_article(int(user_id), intitution_id="https://openalex.org/I17974374")
    else:
        print(_("Param user_id is required."))
