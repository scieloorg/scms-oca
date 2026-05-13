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
        type_status_counts = {}
        for row in (
            self.values("document_type", "status")
            .annotate(count=models.Count("id"))
        ):
            type_status_counts[(row["document_type"], row["status"])] = row["count"]
        scielo_dedup_counts = dict(
            self.filter(has_scielo_dedup=True)
            .values("document_type")
            .annotate(count=models.Count("id"))
            .values_list("document_type", "count")
        )
        openalex_counts = dict(
            self.filter(has_openalex_match=True)
            .values("document_type")
            .annotate(count=models.Count("id"))
            .values_list("document_type", "count")
        )
        return {
            "status_counts": status_counts,
            "type_counts": type_counts,
            "type_status_counts": type_status_counts,
            "scielo_dedup_counts": scielo_dedup_counts,
            "openalex_counts": openalex_counts,
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
    pid_v2 = models.CharField(max_length=255, blank=True, default="")
    doi = models.CharField(max_length=500, blank=True, default="")
    isbn = models.CharField(max_length=255, blank=True, default="")
    preprint_id = models.CharField(max_length=255, blank=True, default="")
    dataset_id = models.CharField(max_length=255, blank=True, default="")
    has_openalex_match = models.BooleanField(default=False)
    has_scielo_dedup = models.BooleanField(default=False)
    scielo_dedup_ids = models.JSONField(default=list, blank=True)
    openalex_match_ids = models.JSONField(default=list, blank=True)
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

    def mark_success(self, result=EtlResult.UPDATED, has_openalex_match=False, has_scielo_dedup=False, scielo_dedup_ids=None, openalex_match_ids=None):
        self.status = EtlStatus.SUCCESS
        self.result = result
        self.has_openalex_match = has_openalex_match
        self.has_scielo_dedup = has_scielo_dedup
        self.scielo_dedup_ids = scielo_dedup_ids or []
        self.openalex_match_ids = openalex_match_ids or []
        self.error = None
        self.processed_at = timezone.now()
        self.save(
            update_fields=[
                "status",
                "result",
                "has_openalex_match",
                "has_scielo_dedup",
                "scielo_dedup_ids",
                "openalex_match_ids",
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
