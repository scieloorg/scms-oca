from infrastructure_directory import infrastructure_factory
from institution import institution_factory


def run(*args):
    if args:
        bulk_size = args[0]
    else:
        bulk_size = 1000

    print("Gerando %s Infrastructure Directories.... " % (bulk_size))
    for i in range(0, int(bulk_size)):
        infrastructure_factory.InfrastructureFactory(
            institutions=(institution_factory.InstitutionFactory(),)
        )
