import pandas as pd
from scholarly_articles import models 
from django.db.models import Q


def run():


    def get_articles_from_journal(more_completed_journal, journals): 

        for journal in journals: 
            articles = models.ScholarlyArticles.objects.filter(journal=journal)

            for article in articles:
                article.journal = more_completed_journal
                article.save()

    def clean_journals(): 

        for journal in models.Journals.objects.all():
            
            articles = models.ScholarlyArticles.objects.filter(journal=journal)

            if len(articles) == 0:
                print("Journal with 0 article associated: %s" % journal)
                models.Journals.objects.get(pk=journal.id).delete()
        
    for journal in models.Journals.objects.all():
        journals = models.Journals.objects.filter(
            Q(journal_issn_l=journal.journal_issn_l) | Q(journal_issns=journal.journal_issns) | Q(journal_name=journal.journal_name)
        )
        
        if journals:
            if len(journals) > 1 and len(journals) <= 10: 

                print("Periódicos em duplicidade: ", str(journal.journal_issn_l), str(journal.journal_issns), str(journal.journal_name), len(journals))
                
                for __ in journals:
                    if __.journal_issn_l and __.journal_issns and __.journal_name:
                        more_completed_journal = __
                        continue
                    if __.journal_issn_l and __.journal_issns:
                        more_completed_journal = __
                        continue
                    if __.journal_issn_l and __.journal_name:
                        more_completed_journal = __
                        continue
                    if __.journal_issns and __.journal_name:
                        more_completed_journal = __
                        continue
                    if __.journal_issn_l or __.journal_issns or __.journal_name:
                        more_completed_journal = __
                        continue

                get_articles_from_journal(more_completed_journal, journals)
    
    clean_journals()
     