from django.apps import AppConfig


class InfrastructureDirectoryConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "infrastructure_directory"

    def ready(self):
        from . import signals  # noqa: F401
