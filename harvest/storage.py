from pathlib import Path

from django.core.files.storage import FileSystemStorage


def global_metrics_upload_path(instance, filename):
    return f"global_metrics_uploads/{Path(filename).name}"


class OverwriteStorage(FileSystemStorage):
    def get_available_name(self, name, max_length=None):
        if self.exists(name):
            self.delete(name)
        return name


overwrite_media_storage = OverwriteStorage()
