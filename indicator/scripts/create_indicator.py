from indicator import tasks, controller


def evolution_of_scientific_production_all(creator_id, years_number=5):
    tasks.task_evolution_of_scientific_production_all.apply_async(
        args=(creator_id, years_number))


def journals_numbers(creator_id):
    tasks.task_journals_numbers_all.apply_async(args=(creator_id, ))


def directory_numbers(creator_id):
    tasks.task_directory_numbers_all.apply_async(args=(creator_id, ))


def run(indicator_type):
    if indicator_type == "action":
        directory_numbers(1)
    elif indicator_type == "sciprod":
        evolution_of_scientific_production_all(1)
    else:
        print("Expected action or sciprod")
    # journals_numbers(creator_id=1)
