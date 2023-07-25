import os 
from django.utils.translation import gettext as _

from article.tasks import concat_article_sucupira_detail, concat_author_sucupira


def run(production_file_csv, detail_file_csv, authors=None, sync=0, file_name="sucupira_article.csv"):
    """
    Concate the a file with the article production in CAPES
    """
    sync = bool(int(sync))
    authors = authors.split(",")

    if production_file_csv and detail_file_csv:
        if os.path.isfile(production_file_csv) and os.path.isfile(detail_file_csv):
            if sync: 
                df = concat_article_sucupira_detail(production_file_csv, detail_file_csv)
                
                if authors:
                    ddfau = concat_author_sucupira(df, authors)
                    ddfau.to_csv(file_name, index=False)
            else:
                concat_article_sucupira_detail.apply_async(args=(production_file_csv, detail_file_csv, True))
        else:
            print(_("It looks like the given path is not a file!"))