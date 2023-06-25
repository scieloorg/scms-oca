from indicator import sciprod
from indicator import directory


def run(indicator_type, min_items=None):
    min_items = min_items and int(min_items)
    if indicator_type == "action":
        directory.schedule_indicators_tasks(min_items)

    elif indicator_type == "sciprod":
        sciprod.schedule_indicators_tasks(min_items)
    else:
        print("Expected action or sciprod")
    # journals_numbers(creator_id=1)
