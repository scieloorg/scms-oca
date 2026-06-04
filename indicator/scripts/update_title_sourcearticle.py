import warnings
warnings.warn(
    "indicator.scripts is deprecated.",
    DeprecationWarning,
    stacklevel=2
)
from article import models


def run():
    
    for article in models.SourceArticle.objects.filter(title__isnull=True).iterator():
        if article.raw:
            if "title" in article.raw:
                article.title = article.raw.get("title")
                article.save()