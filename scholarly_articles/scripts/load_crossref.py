from scholarly_articles.tasks import load_crossref

def run(from_update_date=2012, until_update_date=2012):
    if from_update_date and until_update_date:
        load_crossref.apply_async(args=(from_update_date, until_update_date))
    else:
        print('from_update_date and until_update_date is required.')
    