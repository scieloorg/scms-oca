from django.apps import AppConfig


class PolicyDirectoryConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "policy_directory"

    def ready(self):
        from . import signals  # noqa: F401
