
from policy_directory import policy_factory
from location import location_factory
from institution import institution_factory


def run(*args):

    if args:
        bulk_size = args[0]
    else:
        bulk_size = 1000

    print("Gerando %s Policy Directories.... " % (bulk_size))
    for i in range(0, int(bulk_size)):
        policy_factory.PolicyFactory(institutions=(institution_factory.InstitutionFactory(),))
