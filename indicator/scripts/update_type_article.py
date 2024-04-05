from article import models


def run():
    
    for article in models.Article.objects.filter(type__isnull=True).iterator():

        if article.doi:
            sarticles = models.SourceArticle.objects.filter(doi=article.doi)
        else:
            sarticles = models.SourceArticle.objects.filter(title=article.title)

        print(sarticles)
        for sa in sarticles:
            if sa.raw:
                article.type = sa.raw.get("type")
                article.save()
