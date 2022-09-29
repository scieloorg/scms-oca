from indicator import controller
from institution.models import Institution
from usefulmodels.models import Action

# def run():
#     for institution in Institution.objects.all():

#     indicator = controller.generate_indicator(
#         institution="Universidade de São Paulo",
#         practice="literatura em acesso aberto",
#         action=None,
#         classification=None,
#         thematic_area=None,
#         start_date=None,
#         end_date=None,
#         location=None,
#         return_data=True,
#         return_rows=True,
#     )

#     indicator.creator_id = 1
#     indicator.save()


def generate_institutions_indicators():
    creator_id = 1
    for action in Action.objects.all():
        title = f"Número de {action} [QUALIFICATION_AND_PRACTICE] no contexto institutional"
        controller.generate_indicators_in_institutional_context(
            title, action, creator_id)


def generate_geographical_indicators():
    creator_id = 1
    for action in Action.objects.all():
        title = f"Número de {action} [QUALIFICATION_AND_PRACTICE] no contexto geográfico"
        controller.generate_indicators_in_geographic_context(
            title, action, creator_id)


def run():
    generate_institutions_indicators()
    generate_geographical_indicators()
