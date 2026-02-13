from django.apps import AppConfig


class EducationDirectoryConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "education_directory"

    def ready(self):
        from . import signals  # noqa: F401
