from article import models

def run():
    """
    Clean Article and associted models.
    """
    models.Journal.objects.all().delete()
    models.Contributor.objects.all().delete()
    models.Article.objects.all().delete()
    models.Program.objects.all().delete()
    models.Affiliation.objects.all().delete()
    models.License.objects.all().delete()
