import orjson

from scholarly_articles import models
from django.db.utils import DataError

from datetime import date


def load(line, row, user, file_source):
    """
    Create the record of a loads.

    Param row is a dict content the data to create each loads records.

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
        params = {'doi': doi, 'source': file_source}
        if doi:
            print("Line: %s, id: %s" % (line + 1, doi))
            raw_record = models.RawRecord.objects.filter(**params)
            if len(raw_record) == 0:
                raw_record = models.RawRecord()
                raw_record.doi = doi
                raw_record.harvesting_creation = date.today()
            else:
                raw_record = raw_record[0]
            raw_record.year = row.get('year')
            raw_record.resource_type = row.get('genre')
            raw_record.source = file_source
            raw_record.json = row
            raw_record.save()
    except Exception as e:
        try:
            error = models.ErrorLog()
            error.error_type = str(type(e))
            error.error_message = str(e)[:255]
            error.error_description = "Erro on processing the lines from a .json file to RawRecord model."
            error.data_reference = "line:%s" % str(line + 1)
            error.data = row
            error.data_type = ' '.join([file_source, "JSON"])
            error.creator = user
            error.save()
        except (DataError, TypeError):
            pass