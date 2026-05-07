from django.db import models


class EtlStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    PROCESSING = "processing", "Processing"
    SUCCESS = "success", "Success"
    FAILED = "failed", "Failed"
    SKIPPED = "skipped", "Skipped"


class EtlResult(models.TextChoices):
    CREATED = "created", "Created"
    UPDATED = "updated", "Updated"
    MERGED = "merged", "Merged"
    UNCHANGED = "unchanged", "Unchanged"
    SKIPPED = "skipped", "Skipped"
    ERROR = "error", "Error"


__all__ = [
    "EtlResult",
    "EtlStatus",
]
