from scholarly_articles import models
from django.db.utils import DataError


def load(articles):
    try:
        for article in articles:  
            journal = create_journal(article['container-title'][0])
            contributors = create_contributors(article['author'])

            scholary_article, created = models.ScholarlyArticles.objects.update_or_create(
                doi=article['DOI'],
                defaults={
                    'title': article['title'][0],
                    'volume': article['volume'],
                    'source': article['source'].upper(),
                    'journal': journal,
                }
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


def create_journal(journal_name):
    journal, created = models.Journals.objects.get_or_create(
        journal_name=journal_name
    )
    return journal


def create_contributors(authors):
    contributors = []
    date_author = ['family', 'given', 'orcid', 'affiliation']
    for author in authors:
        # Caso esteja faltando alguns dos dados (family, given, orcid)
        # ele atribui uma string vazia ao campo.
        field = {field: author.get(field, '') for field in date_author}

        affiliation = create_affiliation(field['affiliation'])
        
        contributor, created = models.Contributors.objects.get_or_create(
            family=field['family'],
            given=field['given'],
            orcid=field['orcid'],
            affiliation=affiliation,
        )
        contributors.append(contributor)
    return contributors


def create_affiliation(author):
    affiliation, created = models.Affiliations.objects.get_or_create(
        name=author[0]['name'],
    )
    return affiliation