from scholarly_articles import models
from django.db.utils import DataError

def load(line, row, user):
    try:
        for authors in row['Authors with affiliations'].split(';'):
            author, affiliation = authors.split(',')[0], ','.join(authors.split(',')[1:])
            supplementary = models.SupplementaryData.objects.filter(author=author)
            if len(supplementary) == 0:
                supplementary = models.SupplementaryData()
                supplementary.author = author
            supplementary.doi = row['DOI']
            supplementary.source_title = row['Source title']
            supplementary.volume = row['Volume']
            supplementary.issue = row['Issue']
            supplementary.affiliation = affiliation
            supplementary.save()
    except Exception as e:
        try:
            error = models.ErrorLog()
            error.error_type = str(type(e))
            error.error_message = str(e)[:255]
            error.error_description = "Erro on processing the lines from a .csv file to supplementary model."
            error.data_reference = "line:%s" % str(line + 1)
            error.data = row
            error.data_type = "Supplementary CSV"
            error.creator = user
            error.save()
        except (DataError, TypeError):
            pass