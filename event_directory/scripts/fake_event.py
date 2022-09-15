from event_directory import models

from event_directory import event_factory
from location import location_factory
from institution import institution_factory


def run(*args):

    if args:
        bulk_size = args[0]
    else:
        bulk_size = 1000

    print("Gerando %s Event Directories.... " % (bulk_size))
    for i in range(0, int(bulk_size)):
        event_factory.EventFactory(locations=(location_factory.LocationFactory(),),
                                   organizations=(institution_factory.InstitutionFactory(),))
