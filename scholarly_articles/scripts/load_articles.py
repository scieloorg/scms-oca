from django.contrib.auth import get_user_model

from scholarly_articles.unpaywall import load_data

User = get_user_model()

def run():
    """
    Load the article to ScholarlyArticles.
    """
    user = User.objects.get(id=1)

    load_data.load(from_year=1900, resource_type='journal-article', is_paratext=False, user=user)

