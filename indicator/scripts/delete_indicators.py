from indicator.models import Indicator


def run():
    Indicator.delete()
