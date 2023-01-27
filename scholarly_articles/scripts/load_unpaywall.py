from scholarly_articles.tasks import load_unpaywall


def run(user_id, file_path):

    if file_path and user_id:
        load_unpaywall.apply_async(args=(user_id, file_path))
    elif not file_path:
        print("The path to unpaywall file is required.")
    elif not user_id:
        print("User id is required.")
