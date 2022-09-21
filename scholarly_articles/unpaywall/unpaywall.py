import orjson

from scholarly_articles import models
from django.db.utils import DataError

from datetime import date


def load(line, row, user):
    """
    Create the record of a unpaywall.

    Param row is a dict content the data to create each unpaywall records.

    Something like this:

        {'best_oa_location': None,
        'data_standard': 2,
        'doi': '10.1002/psp.2296',
        'doi_url': 'https://doi.org/10.1002/psp.2296',
        'first_oa_location': None,
        'genre': 'journal-article',
        'has_repository_copy': False,
        'is_oa': False,
        'is_paratext': True,
        'journal_is_in_doaj': False,
        'journal_is_oa': False,
        'journal_issn_l': '1544-8444',
        'journal_issns': '1544-8444,1544-8452',
        'journal_name': 'Population, Space and Place',
        'oa_locations': [],
        'oa_locations_embargoed': [],
        'oa_status': 'closed',
        'published_date': '2020-01-07',
        'publisher': 'Wiley',
        'title': 'Trap or opportunity—What role does geography play in the use of '
                'cash for childcare?',
        'updated': '2021-04-02T00:47:21.884997',
        'year': 2020,
        'z_authors': [{'ORCID': 'http://orcid.org/0000-0002-4877-2961',
                    'affiliation': [{'name': 'Norwegian Social Research Oslo '
                                                'Metropolitan University  Oslo '
                                                'Norway'}],
                    'authenticated-orcid': False,
                    'family': 'Magnusson Turner',
                    'given': 'Lena',
                    'sequence': 'first'},
                    {'ORCID': 'http://orcid.org/0000-0002-4536-9229',
                    'affiliation': [{'name': 'Department of Social and Economic '
                                                'Geography Uppsala University  '
                                                'Uppsala Sweden'}],
                    'authenticated-orcid': False,
                    'family': 'Östh',
                    'given': 'John',
                    'sequence': 'additional'}]}

    """
    try:
        row = orjson.loads(row)
        doi = row.get('doi')
        if doi:
            print("Line: %s, id: %s" % (line + 1, doi))
            rawunpaywall = models.RawUnpaywall.objects.filter(doi=doi)
            if len(rawunpaywall) == 0:
                rawunpaywall = models.RawUnpaywall()
                rawunpaywall.doi = doi
                rawunpaywall.harvesting_creation = date.today()
            else:
                rawunpaywall = rawunpaywall[0]
            rawunpaywall.is_paratext = row.get('is_paratext')
            rawunpaywall.year = row.get('year')
            rawunpaywall.resource_type = row.get('genre')
            try:
                rawunpaywall.update = row.get('updated')[:10]
            except TypeError:
                pass
            rawunpaywall.json = row
            rawunpaywall.save()
    except Exception as e:
        try:
            error = models.ErrorLog()
            error.error_type = str(type(e))
            error.error_message = str(e)[:255]
            error.error_description = "Erro on processing the lines from a .json file to rawunpaywall model."
            error.data_reference = "line:%s" % str(line + 1)
            error.data = row
            error.data_type = "Unpaywall JSON"
            error.creator = user
            error.save()
        except (DataError, TypeError):
            pass