from django.db.utils import DataError

from scholarly_articles import models


class ArticleSaveError(Exception):
    ...

class JournalSaveError(Exception):
    ...

class ContributorSaveError(Exception):
    ...

class AffiliationSaveError(Exception):
    ...

class SourceSaveError(Exception):
    ...


def get_params(row, attribs):
    params = {}
    for att in attribs:
        if row.get(att):
            params[att] = row.get(att)
    return params

def get_source(source):
    source_model = models.Source()
    source_model.source = source
    try:
        source_model.save()
    except (DataError, TypeError) as e:
        raise SourceSaveError(e)
    return source_model


def load_article(row, source):
    articles = models.ScholarlyArticle.objects.filter(doi=row.get('doi'))
    try:
        article = articles[0]
    except IndexError:
        article = models.ScholarlyArticle()
        article.doi = row.get('doi')

    registered_data = (article.title, article.volume, article.open_access_status, article.apc, article.journal)
    row_data = (row.get("title"), row.get("volume"), row.get("open_access_status"), row.get("apc"), row.get("journal"))
    change = registered_data != row_data

    article.title = article.title or row.get('title')
    article.volume = article.volume or row.get('volume')
    article.number = article.number or row.get('number')
    article.year = article.year or row.get('year')
    article.open_access_status = article.open_access_status or row.get('oa_status')
    if len(row.get('oa_locations')) > 0:
        article.use_license = article.use_license or row.get('oa_locations')[0].get('license')
    article.apc = article.apc or row.get('apc')
    article.journal = article.journal or load_journal(row, source)
    try:
        article.save()
    except (DataError, TypeError) as e:
        raise ArticleSaveError(e)

    if change:
        article.sources.add(get_source(source))
        article.save()

    for author in row.get('z_authors') or []:
        contributor = get_one_contributor(author, source)
        article.contributors.add(contributor)
        article.save()

    return article


def load_journal(row, source):
    attribs = ['journal_issns', 'journal_issn_l', 'journal_name']
    params = get_params(row, attribs)

    journals = models.Journal.objects.filter(**params)
    try:
        journal = journals[0]
    except IndexError:
        journal = models.Journal()

    registered_data = (journal.journal_is_in_doaj, journal.journal_issns, journal.journal_issn_l,
                       journal.journal_name, journal.publisher)
    row_data = (row.get('journal_is_in_doaj'), row.get('journal_issns'), row.get('journal_issn_l'),
                row.get('journal_name'), row.get('publisher'))
    change = registered_data != row_data

    journal.journal_is_in_doaj = journal.journal_is_in_doaj or row.get('journal_is_in_doaj')
    journal.journal_issns = journal.journal_issns or row.get('journal_issns')
    journal.journal_issn_l = journal.journal_issn_l or row.get('journal_issn_l')
    journal.journal_name = journal.journal_name or row.get('journal_name')
    journal.publisher = journal.publisher or row.get('publisher')
    try:
        journal.save()
    except (DataError, TypeError) as e:
        raise JournalSaveError(e)

    if change:
        journal.sources.add(get_source(source))
        journal.save()

    return journal


def get_one_contributor(author, source):
    attribs = ['family', 'given']
    params = get_params(author, attribs)
    if author.get('ORCID'):
        params['orcid'] = author.get('ORCID')

    contributors = models.Contributor.objects.filter(**params)
    try:
        contributor = contributors[0]
    except IndexError:
        contributor = models.Contributor()

    registered_data = (contributor.family, contributor.given, contributor.orcid, contributor.authenticated_orcid)
    row_data = (author.get('family'), author.get('given'), author.get('ORCID'), author.get('authenticated-orcid'))
    change = registered_data != row_data

    contributor.family = contributor.family or author.get('family')
    contributor.given = contributor.given or author.get('given')
    contributor.orcid = contributor.orcid or author.get('ORCID')
    contributor.authenticated_orcid = contributor.authenticated_orcid or author.get('authenticated-orcid')

    try:
        contributor.save()
    except (DataError, TypeError) as e:
        raise ContributorSaveError(e)

    if change:
        contributor.sources.add(get_source(source))
        contributor.save()

    if author.get('affiliation'):
        aff = load_affiliation(author.get('affiliation')[0].get('name'), source)
        contributor.affiliation.add(aff)
        contributor.save()

    return contributor


def load_affiliation(affiliation_name, source):
    if affiliation_name:
        try:
            affiliations = models.Affiliation.objects.filter(name=affiliation_name)
            affiliation = affiliations[0]
        except IndexError:
            affiliation = models.Affiliation()
            affiliation.name = affiliation_name
            affiliation.source = source
        try:
            affiliation.save()
        except (DataError, TypeError) as e:
            raise AffiliationSaveError(e)

        return affiliation


def load(from_year, user):
    """
    Load all data with a specific resource_type and year from RawUnpaywall model
    to ScholarlyArticles model.

    Param from_year: Is a interger, example: 2000
    Param resource_type: Is a string, that represent a type in RawUnpaywall
    Param user: The user instance
    """

    # About iterator: https://docs.djangoproject.com/en/3.2/ref/models/querysets/#django.db.models.query.QuerySet.iterator
    raw_record = models.RawRecord.objects.filter(year__gte=from_year).iterator()
    # rawunpaywall = models.RawUnpaywall.objects.filter(year__gte=from_year, resource_type=resource_type)
    for item in raw_record:
        try:
            load_article(item.json, item.source)
        except (ArticleSaveError, JournalSaveError, ContributorSaveError, AffiliationSaveError) as e:
            try:
                error = models.ErrorLog()
                error.error_type = str(type(e))
                error.error_message = str(e)[:255]
                error.error_description = "Erro on processing the RawRecord to ScholarlyArticles."
                error.data_reference = "id:%s" % str(item.id)
                error.data = item.json
                error.data_type = "ScholarlyArticles"
                error.creator = user
                error.save()
            except (DataError, TypeError):
                pass
