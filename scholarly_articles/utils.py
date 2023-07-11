from django.db.models import Q
from scholarly_articles import models


def check_articles_journals():
    """
    This function return journals that dont have article associate.

    return a list of journals without articles associate.
    """
    journals_without_articles = []

    for journal in models.Journals.objects.all():
        articles = models.ScholarlyArticles.objects.filter(journal=journal)

        if len(articles) == 0:
            journals_without_articles.append(models.Journals.objects.get(pk=journal.id))

    return journals_without_articles


def check_duplicate_journal(journal=None):
    """
    This function return if there is duplicate journals.

    Return a list with the reference to journal and the size of the duplications.
    """

    if journal.journal_issn_l and journal.journal_issns and journal.journal_name:
        journals = models.Journals.objects.filter(
            Q(journal_issn_l=journal.journal_issn_l)
            | Q(journal_issns__icontains=journal.journal_issns)
            | Q(journal_name__iexact=journal.journal_name)
        )
    elif journal.journal_issn_l and journal.journal_issns:
        journals = models.Journals.objects.filter(
            Q(journal_issn_l=journal.journal_issn_l)
            | Q(journal_issns__icontains=journal.journal_issns)
        )
    elif journal.journal_issns and journal.journal_name:
        journals = models.Journals.objects.filter(
            Q(journal_issns__icontains=journal.journal_issns)
            | Q(journal_name__iexact=journal.journal_name)
        )
    elif journal.journal_issn_l and journal.journal_name:
        journals = models.Journals.objects.filter(
            Q(journal_issn_l=journal.journal_issn_l)
            | Q(journal_name__iexact=journal.journal_name)
        )
    elif journal.journal_issn_l:
        journals = models.Journals.objects.filter(
            Q(journal_issn_l=journal.journal_issn_l)
        )
    elif journal.journal_issns:
        journals = models.Journals.objects.filter(
            Q(journal_issns__icontains=journal.journal_issns)
        )
    elif journal.journal_name:
        journals = models.Journals.objects.filter(
            Q(journal_name__iexact=journal.journal_name)
        )

    if journals:
        qt = len(journals)
        if qt > 1:
            return journals


def check_articles_without_journals():
    """
    This function return articles without journal associate.

    Return a list of articles(object)
    """
    articles_without_journals = []

    for article in models.ScholarlyArticles.objects.iterator():
        if not article.journal:
            articles_without_journals.append(article)

    return articles_without_journals


def reassignment_articles(cast_journal, journals):
    """
    This function receive a casted journal and a list of journals to search by article.

    This found articles must be reassignment to the casted journal.

    Return a list of articles reassigned.
    """
    articles = None

    for journal in journals:
        articles = models.ScholarlyArticles.objects.filter(journal=journal)

        for article in articles:
            article.journal = cast_journal
            article.save()  

    return articles

