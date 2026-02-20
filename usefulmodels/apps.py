from django.apps import AppConfig


class UsefulmodelsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "usefulmodels"

    def ready(self):
        from . import signals  # noqa: F401
