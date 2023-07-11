from scholarly_articles.tasks import sanitize_all_journals


def run(user_id):
    if user_id:
        sanitize_all_journals.apply_async(args=(user_id, ))