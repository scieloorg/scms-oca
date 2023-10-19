from scholarly_articles.tasks import sanitize_authors


def run(user_id):
    if user_id:
        sanitize_authors.apply_async(args=(user_id, ))