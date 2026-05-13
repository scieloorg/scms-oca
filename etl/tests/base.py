from django.core.management import call_command
from django.test import TestCase


class EtlTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("add_rules")
