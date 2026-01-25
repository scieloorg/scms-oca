from django.apps import AppConfig


class HarvestConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "harvest"

    def ready(self):
        from . import signals  # noqa: F401
