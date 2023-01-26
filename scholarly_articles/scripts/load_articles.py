from scholarly_articles.tasks import load_journal_articles


def run(user_id):
    """
    Load the article to ScholarlyArticles.
    """
    load_journal_articles.apply_async(
        kwargs={"user_id": user_id, "from_year": 1900,
                "resource_type": "journal-article"})
