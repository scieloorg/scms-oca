import logging
from indicator import tasks, controller


def evolution_of_scientific_production(creator_id, category, context=None, years_number=5):
    # tasks.task_evolution_of_scientific_production_all.apply_async(
    #     args=(creator_id, years_number))
    tasks.task_evolution_of_scientific_production.apply_async(
        args=(creator_id, category, context, years_number)
    )


def journals_numbers(creator_id):
    tasks.task_journals_numbers_all.apply_async(args=(creator_id, ))


def directory_numbers(creator_id, category=None, context_id=None):
    tasks.task_directory_numbers.apply_async(
        args=(creator_id, category, context_id)
    )


def run(indicator_type, category=None, context=None, years_number=None):
    years_number = years_number and int(years_number)
    logging.info((category, context, years_number))
    if indicator_type == "action":
        if category:
            # directory_numbers(1)
            directory_numbers(1, category, context)
        else:

            for cat in (None, 'CA_PRACTICE', 'THEMATIC_AREA'):
                for ctxt in (None, 'THEMATIC_AREA', 'LOCATION', 'INSTITUTION'):
                    if cat == ctxt:
                        continue
                    try:
                        logging.info((cat, ctxt))
                        directory_numbers(1, cat, ctxt)
                    except Exception as e:
                        logging.exception(e)
                        continue

    elif indicator_type == "sciprod":
        if category:
            evolution_of_scientific_production(1, category, context, years_number)
        else:
            for cat in ('OPEN_ACCESS_STATUS', 'USE_LICENSE'):
                for ctxt in (None, 'AFFILIATION_UF', 'AFFILIATION', ):
                    try:
                        logging.info((cat, ctxt, years_number))
                        evolution_of_scientific_production(1, cat, ctxt, years_number)
                    except Exception as e:
                        logging.exception(e)
                        continue
    else:
        print("Expected action or sciprod")
    # journals_numbers(creator_id=1)
