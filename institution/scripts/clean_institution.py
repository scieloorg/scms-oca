from django.utils.translation import gettext as _

from institution import models

def run():
    """
    Clean Article and associted models.
    """
    models.SourceInstitution.objects.all().delete()
