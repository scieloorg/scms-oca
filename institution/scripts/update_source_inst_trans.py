from django.utils.translation import gettext as _

from institution.models import SourceInstitution, InstitutionTranslateName

from core.utils.utils import nestget

def run():
    """
    This script update the Source Institution with the translations.
    """
    for inst in SourceInstitution.objects.all().iterator():
        if inst.raw:    
            for lang, name in nestget(inst.raw, "international", "display_name").items():
                print(lang, name)
                InstitutionTranslateName.create_or_update(language=lang, name=name, source_institution=inst)
