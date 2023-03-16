import factory
from factory.django import DjangoModelFactory

from core.users import user_factory
from location.models import Location
from usefulmodels.usefulmodels_factory import CityFactory, CountryFactory, StateFactory

factory.Faker._DEFAULT_LOCALE = "pt_BR"


class LocationFactory(DjangoModelFactory):
    class Meta:
        model = Location

    creator = factory.SubFactory(user_factory.UserFactory)
    city = factory.SubFactory(CityFactory)
    state = factory.SubFactory(StateFactory)
    country = factory.SubFactory(CountryFactory)
