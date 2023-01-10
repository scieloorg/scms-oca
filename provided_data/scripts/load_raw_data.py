from provided_data.tasks import load_raw_data


def run(*args):

    if args:
        load_raw_data.apply_async(kwargs={"file_path": args[0]})
    else:
        print("The path to unpaywall file is required.")
