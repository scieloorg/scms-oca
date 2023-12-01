from article.tasks import load_articles_from_sucupira

def run():
    load_articles_from_sucupira.apply_async()