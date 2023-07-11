from scholarly_articles.tasks import remove_orphans_journals


def run(user_id):
    if user_id:
        remove_orphans_journals.apply_async(args=(user_id, ))