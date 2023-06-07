from scholarly_articles.tasks import load_sucupira


def run(file_path, user_id):
    """
    Load the article from sucupira to ScholarlyArticles.
    """
    
    if file_path:
        load_sucupira.apply_async(args=(file_path, user_id))
    elif not file_path:
        print("The path to .csv file is required.")
    elif not user_id:
        print("User id is required.")
    