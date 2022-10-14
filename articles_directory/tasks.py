from django.contrib.auth import get_user_model

from config import celery_app
from articles_directory.scripts import load_articles
from scholarly_articles import models

User = get_user_model()


@celery_app.task()
def load(user_id):
    """
    Load the data from ScholarlyArticles model to ArticlesDirectory.

    Sync or Async function

    Param user: The user id passed by kwargs on tasks.kwargs
    """
    user = User.objects.get(id=user_id)

    articles_unpaywall = models.ScholarlyArticles.objects.all()
    for article_unpaywall in articles_unpaywall:
        load_articles.load(article_unpaywall)
