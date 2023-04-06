from scholarly_articles import models
from django.db.utils import DataError

from core.utils import utils


def load(articles):
    """
    Load the article data do models.ScholarlyArticles, cheching by DOI if the article already exists.

    Example of article data:
    [
        {'DOI': '10.1590/s1516-14391999000400004',
        'author': [{'affiliation': [{'name': 'UNESP,  Brazil; UFSCar,  Brazil'}],
                    'family': 'Cavalheiro',
                    'given': 'A.A.',
                    'sequence': 'first'},
                    {'affiliation': [{'name': 'UNESP,  Brazil; UFSCar,  Brazil'}],
                    'family': 'Zaghete',
                    'given': 'M.A.',
                    'sequence': 'additional'},
                    {'affiliation': [{'name': 'UNESP,  Brazil; UFSCar,  Brazil'}],
                    'family': 'Santos',
                    'given': 'C.O. Paiva',
                    'sequence': 'additional'},
                    {'affiliation': [{'name': 'UNESP,  Brazil; UFSCar,  Brazil'}],
                    'family': 'Varela',
                    'given': 'J.A.',
                    'sequence': 'additional'},
                    {'affiliation': [{'name': 'UNESP,  Brazil; UFSCar,  Brazil'}],
                    'family': 'Longo',
                    'given': 'E.',
                    'sequence': 'additional'}],
        'container-title': ['Materials Research'],
        'issue': '4',
        'issued': {'date-parts': [[1999, 10]]},
        'publisher': 'FapUNIFESP (SciELO)',
        'source': 'Crossref',
        'title': ['Influence of synthesis and processing parameters of the columbite '
                    'precursor on the amount of Perovskite PMN'],
        'type': 'journal-article',
        'volume': '2'}],
        "license": [
          {
            "start": {
              "date-parts": [
                [
                  2020,
                  6,
                  9
                ]
              ],
              "date-time": "2020-06-09T00:00:00Z",
              "timestamp": 1591660800000
            },
            "content-version": "vor",
            "delay-in-days": 8,
            "URL": "http://www.diabetesjournals.org/content/license"
          }
        ],
        }
    ]

    """

    try:

        for article in articles:
            journal = get_or_create_journal(
                utils.nestget(article, "container-title", 0),
                utils.nestget(article, "ISSN")
            )
            contributors = get_or_create_contributor(utils.nestget(article, "author"))
            license = get_or_create_license(utils.nestget(article, "license"))

            (
                scholary_article,
                created,
            ) = models.ScholarlyArticles.objects.update_or_create(
                doi=utils.nestget(article, "DOI"),
                defaults={
                    "title": utils.nestget(article, "title", 0),
                    "volume": utils.nestget(article, "volume"),
                    "source": utils.nestget(article, "source", default="").upper(),
                    "year": utils.nestget(article, "issued", "date-parts", 0, 0),
                    "number": utils.nestget(article, "issue"),
                    "journal": journal,
                    "license": license,
                },
            )
            scholary_article.contributors.set(contributors)

    except Exception as e:
        print(f"Error saving data to scholary article database: {e}")
        try:
            error = models.ErrorLog()
            error.error_type = str(type(e))
            error.error_message = str(e)[:255]
            error.error_description = (
                "Erro on processing the Api Crossref to Scholary Articles model."
            )
            error.data_reference = article
            error.data = articles
            error.data_type = "API Crossref"
            error.save()
        except (DataError, TypeError):
            pass


def get_or_create_journal(journal_name, issns):
    """
    Get or create journal by "issns".

    This function try to get the journal from database, 
    if this find one this function return from database, 
    otherwise create a journal.

    Params:

        ISSNS: This is a list with all ISSNs, example: "ISSN": [ "0012-1797", "1939-327X" ],
    """

    for issn in issns:
        journal = models.Journals.objects.filter(journal_issns__icontains=issn)
        if journal:
            return utils.nestget(journal, 0)
        else: 
            return models.Journals.objects.create(journal_name=journal_name, journal_issns=",".join())
    return None


def get_or_create_contributor(authors):
    """
    Get or create contributor by "family", "given", "ORCID", "affiliation"
    """
    contributors = []
    date_author = ["family", "given", "ORCID", "affiliation"]
    for author in authors:
        # Caso esteja faltando alguns dos dados (family, given, orcid)
        # ele atribui uma string vazia ao campo.
        field = {field: author.get(field, "") for field in date_author}

        affiliation = get_or_create_affiliation(utils.nestget(field, "affiliation"))

        contributor, created = models.Contributors.objects.get_or_create(
            family=utils.nestget(field, "family"),
            given=utils.nestget(field, "given"),
            orcid=utils.nestget(field, "ORCID"),
            affiliation=affiliation,
        )
        contributors.append(contributor)
    return contributors


def get_or_create_affiliation(affiliation):
    """
    Get or create affiliation by "name"
    """
    if affiliation:
        name = utils.nestget(affiliation, 0, "name")
        if name:
            aff, created = models.Affiliations.objects.get_or_create(
                name=name,
            )
            return aff
    return None


def get_or_create_license(license):
    """
    Get or create license by "name"
    """
    if license:
        url = utils.nestget(license, 0, "URL")
        if url:
            lic, created = models.License.objects.get_or_create(
                url=url,
            )
            return lic
    return None
