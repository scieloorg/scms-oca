from education_directory import models

from education_directory import education_factory
from location import location_factory
from institution import institution_factory


def run(*args):

    if args:
        bulk_size = args[0]
    else:
        bulk_size = 1000

    print("Gerando %s Education Directories.... " % (bulk_size))
    for i in range(0, int(bulk_size)):
        education_factory.EducationFactory(locations=(location_factory.LocationFactory(),),
                                           institutions=(institution_factory.InstitutionFactory(),))
