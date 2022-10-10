import orjson

from scholarly_articles import models
from django.db.utils import DataError

from datetime import date


def load(line, row, user):
    """
    Create the record of a supplementary data.

    Param row is a dict content the data to create each supplementary records.

    Something like this:
      {
           "doi":"10.1590/1519-6984.252364",
           "year":2024,
           "genre":"Article",
           "is_oa":true,
           "title":"Morphophysiological changes of Acca sellowiana (Myrtaceae: Myrtoideae) saplings under shade gradient; [Alterações morfofisiológicas em mudas de Acca sellowiana (Myrtaceae: Myrtoideae) sob gradiente de sombreamento]",
           "doi_url":"",
           "updated":"",
           "oa_status":[
              "All Open Access",
              "Gold Open Access"
           ],
           "publisher":"Instituto Internacional de Ecologia",
           "z-authors":[
              {
                 "ORCID":"",
                 "given":"L.R.",
                 "family":"Silva",
                 "sequence":"",
                 "affiliation":[
                    {
                       "name":" Universidade Tecnológica Federal do Paraná – UTFPR, Programa de Pós-Graduação em Agronomia, Câmpus Pato Branco, Paraná, Pato Branco, Brazil"
                    }
                 ],
                 "authenticated-orcid":false
              }
           ],
           "is_paratext":"",
           "journal_name":"Brazilian Journal of Biology",
           "oa_locations":[],
           "data_standard":"",
           "journal_is_oa":"",
           "journal_issns":"",
           "journal_issn_l":"15196984",
           "published_date":"",
           "best_oa_location":null,
           "first_oa_location":null,
           "journal_is_in_doaj":"",
           "has_repository_copy":"",
           "oa_locations_embargoed":[]
        }

    """
    try:
        row = orjson.loads(row)
        doi = row.get('doi')
        if doi:
            print("Line: %s, id: %s" % (line + 1, doi))
            supplementary = models.SupplementaryData.objects.filter(doi=doi)
            if len(supplementary) == 0:
                supplementary = models.SupplementaryData()
                supplementary.doi = doi
            else:
                supplementary = supplementary[0]
            supplementary.year = row.get('year')
            supplementary.json = row
            supplementary.save()
    except Exception as e:
        try:
            error = models.ErrorLog()
            error.error_type = str(type(e))
            error.error_message = str(e)[:255]
            error.error_description = "Error on processing the lines from a .json file to supplementary model."
            error.data_reference = "line:%s" % str(line + 1)
            error.data = row
            error.data_type = "SupplementaryData JSON"
            error.creator = user
            error.save()
        except (DataError, TypeError):
            pass