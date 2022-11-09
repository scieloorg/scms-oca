from . import tasks


def load_official_name():
    tasks.apply_async()


def run():
    load_official_name()
