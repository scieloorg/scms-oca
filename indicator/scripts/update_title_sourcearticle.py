from article import models


def run():
    
    for article in models.SourceArticle.objects.filter(title__isnull=True).iterator():
        if article.raw:
            if "title" in article.raw:
                article.title = article.raw.get("title")
                article.save()