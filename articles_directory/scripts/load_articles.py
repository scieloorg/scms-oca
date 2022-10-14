from scholarly_articles import models as models_source
from articles_directory import models as models_destiny


def get_affiliation_name(article, family):
    """
        Returns the name of an institution (affiliation) from an author's family name

        Param article: Is a object from ScholarlyArticles model
        Param family: Is a string with an author's family name
    """

    for name in article.json.get('z-authors') or []:
        if name.get('family') == family:
            return name.get('affiliation')[0].get('name')


def get_article_supplementary(doi):
    """
        Returns a object from SupplementaryData model whose 'doi' attribute matches the desired record.

        Param doi: is the value of the attribute that is sought.
    """

    try:
        article_supplementary = models_source.SupplementaryData.objects.filter(doi=doi)
        article_supplementary = article_supplementary[0]
    except IndexError:
        article_supplementary = None
    return  article_supplementary


def get_article(article_unpaywall):
    """
        Returns an object Articles model (ArticlesDirectory) loaded with the data
        obtained from an object ScholarlyArticles model.

        Param article_unpaywall: Is a object from ScholarlyArticles model.
    """
    try:
        article = models_destiny.Articles.objects.filter(doi=article_unpaywall.doi)
        article = article[0]
    except IndexError:
        article = models_destiny.Articles()
        article.doi = article_unpaywall.doi
    article.title = article_unpaywall.title
    article.volume = article_unpaywall.volume
    article.number = article_unpaywall.number
    article.year = article_unpaywall.year
    article.open_access_status = article_unpaywall.open_access_status
    article.use_license = article_unpaywall.use_license
    article.source = article_unpaywall.source
    article.save()
    return article


def get_journal(article_unpaywall):
    """
        Returns an object Journal model (ArticlesDirectory) loaded with the data
        obtained from an object ScholarlyArticles model.

        Param article_unpaywall: Is a object from ScholarlyArticles model.
    """
    try:
        journal = models_destiny.Journals.objects.filter(journal_issn_l=article_unpaywall.journal.journal_issn_l)
        journal = journal[0]
    except IndexError:
        journal = models_destiny.Journals()
        journal.journal_issn_l = article_unpaywall.journal.journal_issn_l
    journal.journal_issns = article_unpaywall.journal.journal_issns
    journal.journal_name = article_unpaywall.journal.journal_name
    journal.publisher = article_unpaywall.journal.publisher
    journal.journal_is_in_doaj = article_unpaywall.journal.journal_is_in_doaj
    journal.save()
    return journal


def get_affiliation(names, aff):
    """
        Returns an object Affiliation model (ArticlesDirectory) loaded with the data
        obtained from an object ScholarlyArticles model.

        Param names: is a list with names of declared institutions.
        Param aff: is an integer value representing a position (indexer) in the list.
    """
    try:
        affiliation = models_destiny.Affiliations.objects.filter(name=names[aff])
        affiliation = affiliation[0]
    except IndexError:
        affiliation = models_destiny.Affiliations()
        affiliation.name = names[aff]
    affiliation.source = "Unpaywall" if aff == 0 else "Supplementary"
    affiliation.save()
    return affiliation


def get_contributors(contributor, article_unpaywall):
    """
        Returns an object Contributor model (ArticlesDirectory) loaded with the data
        obtained from an object ScholarlyArticles model.

        Param contributor: is a object Contributor from ScholarlyArticles model.
        Param article_unpaywall: is a object ScholarlyArticles from ScholarlyArticles model.
    """
    try:
        author = models_destiny.Contributors.objects.filter(family=contributor.family)
        author = author[0]
    except IndexError:
        author = models_destiny.Contributors()
        author.family = contributor.family
    author.orcid = contributor.orcid
    author.given = contributor.given
    author.authenticated_orcid = contributor.authenticated_orcid
    author.save()

    article_supplementary = get_article_supplementary(article_unpaywall.doi)

    names = [
        contributor.affiliation.name,
        get_affiliation_name(article_supplementary, contributor.family)
    ]

    for aff in range(len(names)):
        if names[aff]:
            affiliation = get_affiliation(names, aff)
            author.affiliation.add(affiliation)
            author.save()

    return author


def load(article_unpaywall):
    """
    Loads the ScholarlyArticles model data into the ArticleDirectory model.

    Param article_unpaywall: Is a object from ScholarlyArticles model
    """

    if article_unpaywall:
        article = get_article(article_unpaywall)
        article.journal = get_journal(article_unpaywall)
        article.save()
        for contributor in article_unpaywall.contributors.all():
            author = get_contributors(contributor, article_unpaywall)
            article.contributors.add(author)
            article.save()
