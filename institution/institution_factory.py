import factory
from factory.django import DjangoModelFactory

from core.users import user_factory
from institution.choices import inst_type
from institution.models import Institution
from location.location_factory import LocationFactory

factory.Faker._DEFAULT_LOCALE = 'pt_BR'

class InstitutionFactory(DjangoModelFactory):

    class Meta:
        model = Institution

    creator = factory.SubFactory(user_factory.UserFactory)

    name = factory.Sequence(lambda n: "Name %03d" % n)
    institution_type = factory.Iterator([ins[0] for ins in inst_type])

    location = factory.SubFactory(LocationFactory)
