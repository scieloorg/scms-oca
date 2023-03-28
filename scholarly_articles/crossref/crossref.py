from scholarly_articles import models
from django.db.utils import DataError


def load(articles):
    try:
        for article in articles:
            scholary_article, created = models.ScholarlyArticles.objects.update_or_create(
                doi=article['DOI'],
                defaults={
                    'title': article['title'][0],
                    'volume': article['volume'],
                    'source': article['source'].upper(),
                }
            )
    except Exception as e:
        print(f"Error: {e}")
        try:
            error = models.ErrorLog()
            error.error_type = str(type(e))
            error.error_message = str(e)[:255]
            error.error_description = (
                "Erro on processing the Api Crossref to Scholary Articles model."
            )
            error.data_reference = article
            error.data = articles
            error.data_type = "API Crossref"
            error.save()
        except (DataError, TypeError):
            pass

