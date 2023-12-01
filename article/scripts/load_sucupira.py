import os
from django.utils.translation import gettext as _

from article.tasks import load_sucupira


def run(
        production_file_csv="article/fixture/br-capes-colsucup-producao-2017a2020-2022-06-22-bibliografica-artpe.csv", 
        detail_file_csv="article/fixture/br-colsucup-prod-detalhe-bibliografica-2017a2020-2022-06-30-artpe.csv", 
        authors="article/fixture/br-capes-colsucup-prod-autor-2017a2020-2022-05-31-bibliografica-artpe-2017.csv,article/fixture/br-capes-colsucup-prod-autor-2017a2020-2022-05-31-bibliografica-artpe-2018.csv,article/fixture/br-capes-colsucup-prod-autor-2017a2020-2022-05-31-bibliografica-artpe-2019.csv,article/fixture/br-capes-colsucup-prod-autor-2017a2020-2022-05-31-bibliografica-artpe-2020.csv", 
        sync=0):
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
