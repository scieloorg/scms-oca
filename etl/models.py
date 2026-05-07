from datetime import timedelta

from django.db import models
from django.utils import timezone


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


class EtlItemProcessQuerySet(models.QuerySet):
    def requeue_stale_processing(self, timeout_minutes: int = 30) -> int:
        stale_before = timezone.now() - timedelta(minutes=timeout_minutes)
        return self.filter(
            status=EtlStatus.PROCESSING,
            updated_at__lt=stale_before,
        ).update(status=EtlStatus.PENDING, error="Processing timeout; requeued")

    def reset_to_pending(self, item_ids: list[int]) -> int:
        return self.filter(id__in=item_ids).update(
            status=EtlStatus.PENDING,
            result="",
            error=None,
            attempts=0,
        )

    def retry_failed(self, item_ids: list[int]) -> int:
        return self.filter(
            id__in=item_ids,
            status=EtlStatus.FAILED,
        ).update(status=EtlStatus.PENDING, error=None)

    def retry_failed_by_type(self, document_type: str) -> int:
        return self.filter(
            document_type=document_type,
            status=EtlStatus.FAILED,
        ).update(status=EtlStatus.PENDING, error=None)

    def get_summary_stats(self) -> dict:
        status_counts = dict(
            self.values("status")
            .annotate(count=models.Count("id"))
            .values_list("status", "count")
        )
        type_counts = dict(
            self.values("document_type")
            .annotate(count=models.Count("id"))
            .values_list("document_type", "count")
        )
        return {
            "status_counts": status_counts,
            "type_counts": type_counts,
        }


class EtlItemProcess(models.Model):
    source_index = models.CharField(max_length=255, db_index=True)
    external_id = models.CharField(max_length=255)
    document_type = models.CharField(max_length=50, db_index=True)
    publication_year = models.PositiveIntegerField(
        null=True,
        blank=True,
        db_index=True,
    )
    source_hash = models.CharField(max_length=64, blank=True)
    status = models.CharField(
        max_length=20,
        choices=EtlStatus.choices,
        default=EtlStatus.PENDING,
        db_index=True,
    )
    result = models.CharField(
        max_length=30,
        choices=EtlResult.choices,
        blank=True,
    )
    attempts = models.PositiveIntegerField(default=0)
    error = models.TextField(null=True, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    objects = EtlItemProcessQuerySet.as_manager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["source_index", "external_id"],
                name="uniq_etl_item_source_external_id",
            )
        ]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["document_type", "publication_year"]),
            models.Index(fields=["updated_at"]),
        ]

    def __str__(self):
        return f"{self.source_index}:{self.external_id} [{self.status}]"

    def mark_processing(self):
        self.status = EtlStatus.PROCESSING
        self.attempts += 1
        self.error = None
        self.save(update_fields=["status", "attempts", "error", "updated_at"])

    def mark_success(self, result=EtlResult.UPDATED):
        self.status = EtlStatus.SUCCESS
        self.result = result
        self.error = None
        self.processed_at = timezone.now()
        self.save(
            update_fields=[
                "status",
                "result",
                "error",
                "processed_at",
                "updated_at",
            ]
        )

    def mark_failed(self, error):
        self.status = EtlStatus.FAILED
        self.result = EtlResult.ERROR
        self.error = str(error)[:5000]
        self.processed_at = timezone.now()
        self.save(
            update_fields=[
                "status",
                "result",
                "error",
                "processed_at",
                "updated_at",
            ]
        )


__all__ = [
    "EtlItemProcess",
    "EtlItemProcessQuerySet",
    "EtlResult",
    "EtlStatus",
]
