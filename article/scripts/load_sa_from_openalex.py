from article.tasks import load_source_articles_from_openalex


def run(size=100):
    load_source_articles_from_openalex.apply_async()