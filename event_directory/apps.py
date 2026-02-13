from django.apps import AppConfig


class EventDirectoryConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "event_directory"

    def ready(self):
        from . import signals  # noqa: F401
