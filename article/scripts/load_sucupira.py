import os
from django.utils.translation import gettext as _

from article.tasks import load_sucupira


def run(production_file_csv, detail_file_csv, authors=None, sync=0):
    """
    Load the sucupira data to article.models.SourceArticle
    """
    sync = bool(int(sync))
    authors = authors.split(",")

    if production_file_csv and detail_file_csv:
        if os.path.isfile(production_file_csv) and os.path.isfile(detail_file_csv):
            if sync: 
                load_sucupira(production_file_csv, detail_file_csv, authors) 
            else:
                load_sucupira.apply_async(args=(production_file_csv, detail_file_csv, authors))
        else:
            print(_("It looks like the given path is not a file!"))
