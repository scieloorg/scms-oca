from datetime import datetime

import factory
from django.contrib.auth import get_user_model
from factory.django import DjangoModelFactory

User = get_user_model()

factory.Faker._DEFAULT_LOCALE = 'pt_BR'

class UserFactory(DjangoModelFactory):

    class Meta:
        model = User
        django_get_or_create = ('username',)

    username = "fake_user"
