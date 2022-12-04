from core import tasks


def run():
    tasks.check_values.apply_async()
