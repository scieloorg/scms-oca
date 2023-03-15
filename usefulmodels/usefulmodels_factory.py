import factory
from factory.django import DjangoModelFactory

from core.users import user_factory
from usefulmodels.choices import regions
from usefulmodels.models import Action, City, Country, Practice, State

factory.Faker._DEFAULT_LOCALE = "pt_BR"


class CityFactory(DjangoModelFactory):
    class Meta:
        model = City
        django_get_or_create = ("name",)

    creator = factory.SubFactory(user_factory.UserFactory)

    name = factory.Faker("city")


class StateFactory(DjangoModelFactory):
    class Meta:
        model = State
        django_get_or_create = ("name",)

    creator = factory.SubFactory(user_factory.UserFactory)

    name = factory.Faker("state")
    acronym = factory.Faker("slug")
    region = factory.Iterator([r[0] for r in regions])


class CountryFactory(DjangoModelFactory):
    class Meta:
        model = Country
        django_get_or_create = ("name",)

    creator = factory.SubFactory(user_factory.UserFactory)

    name = "Brasil"


class PraticeFactory(DjangoModelFactory):
    class Meta:
        model = Practice
        django_get_or_create = ("name",)

    creator = factory.SubFactory(user_factory.UserFactory)

    name = factory.Iterator(
        [
            "menção genérica à CA ou todas as práticas",
            "literatura em acesso aberto",
            "dados abertos de pesquisa",
            "peer review aberto",
            "ciência cidadã",
            "recursos educacionais abertos",
            "outras práticas",
        ]
    )


class ActionFactory(DjangoModelFactory):
    class Meta:
        model = Action
        django_get_or_create = ("name",)

    creator = factory.SubFactory(user_factory.UserFactory)

    name = factory.Iterator(
        [
            "políticas públicas e institucionais",
            "evolução da produção científica",
            "infraestrutura",
            "educação / capacitação",
            "disseminação",
            "documentos",
            "outras",
        ]
    )
