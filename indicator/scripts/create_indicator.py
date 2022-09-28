from indicator import controller
from institution.models import Institution

def run():
    for institution in Institution.objects.all():

    indicator = controller.generate_indicator(
        institution="Universidade de São Paulo",
        practice="literatura em acesso aberto",
        action=None,
        classification=None,
        thematic_area=None,
        start_date=None,
        end_date=None,
        location=None,
        return_data=True,
        return_rows=True,
    )

    indicator.creator_id = 1
    indicator.save()
