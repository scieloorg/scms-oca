from scholarly_articles.tasks import load_unpaywall


def run(*args):

    if args:
        load_unpaywall.apply_async(kwargs={"file_path": args[0]})
    else:
        print("The path to unpaywall file is required.")
