from datetime import timedelta
from fnmatch import fnmatch

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from wagtail.admin.panels import FieldPanel
from wagtail_json_widget.widgets import JSONEditorWidget

from harvest.utils import clean_source_payload
from etl.documents import (
    SciELOArticleInputDocument,
    SciELOBookInputDocument,
    SciELODatasetInputDocument,
    SciELOPreprintInputDocument,
)
from etl.transform.normalizers import normalize_document_type_for_etl


DOCUMENT_TYPE_CHOICES = (
    ("article", "Article"),
    ("book", "Book"),
    ("book-chapter", "Book chapter"),
    ("preprint", "Preprint"),
    ("dataset", "Dataset"),
)

INPUT_DOCUMENT_KIND_CHOICES = (
    ("article", "SciELO Article"),
    ("book", "SciELO Book"),
    ("preprint", "SciELO Preprint"),
    ("dataset", "SciELO Dataset"),
)

DEFAULT_OPENALEX_VALIDATION_RULES = {
    "year_tolerance": 1,
    "require_openalex_year": True,
    "require_source_match": False,
    "source_similarity_threshold": 0.80,
    "title_match_threshold": 0.85,
    "title_reject_threshold": 0.80,
    "min_score": 50,
    "strict_min_score": 60,
    "doi_score": 50,
    "year_exact_score": 30,
    "year_close_score": 20,
    "isbn_score": 35,
    "source_id_score": 40,
    "source_title_score": 30,
    "title_score": 30,
    "isbn_requires_title_match": False,
    "isbn_title_threshold": 0.80,
}

DEFAULT_OPENALEX_QUERY_RULES = {
    "exclude_is_xpac": False,
    "publication_year_min": None,
    "publication_year_max": None,
}


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


class EtlPipelineConfigManager(models.Manager):
    def enabled(self):
        return self.filter(enabled=True).order_by("id")

    def enabled_document_types(self):
        return tuple(
            dict.fromkeys(
                self.enabled().values_list(
                    "default_document_type",
                    flat=True,
                )
            )
        )

    def get_for_source(self, source_index: str, source_payload: dict | None = None):
        config = self.select_for_source(source_index, source_payload)
        if config:
            return config
        raise ValueError(f"No enabled ETL pipeline config for source index: {source_index}")

    def select_for_source(self, source_index: str, source_payload: dict | None = None):
        configs = [
            config
            for config in self.enabled()
            if config.matches_input_index(source_index)
        ]
        if not configs:
            return None

        payload_type = self._source_payload_document_type(source_payload)
        if payload_type:
            typed_configs = [
                config
                for config in configs
                if normalize_document_type_for_etl(config.default_document_type) == payload_type
            ]
            if len(typed_configs) == 1:
                return typed_configs[0]
            if len(typed_configs) > 1:
                raise ValueError(
                    f"Multiple enabled ETL pipeline configs for source index "
                    f"{source_index} and document type {payload_type}"
                )

        if len(configs) == 1:
            return configs[0]

        raise ValueError(
            f"Multiple enabled ETL pipeline configs for source index {source_index}; "
            "source payload type is required"
        )

    def get_enabled_by_name(self, name: str):
        try:
            return self.enabled().get(name=name)
        except self.model.DoesNotExist as exc:
            raise ValueError(f"No enabled ETL pipeline config named: {name}") from exc

    def resolve_names(self, target_type: str) -> list[str]:
        if target_type == "all":
            return list(self.enabled().values_list("name", flat=True))
        if not self.enabled().filter(name=target_type).exists():
            raise ValueError(f"Unknown or disabled ETL target type: {target_type}")
        return [target_type]

    @staticmethod
    def _source_payload_document_type(source_payload: dict | None) -> str | None:
        if not source_payload:
            return None
        payload = clean_source_payload(source_payload)
        raw_type = payload.get("type") or payload.get("document_type")
        if not raw_type:
            return None
        return normalize_document_type_for_etl(raw_type)


class EtlPipelineConfig(models.Model):
    name = models.CharField(max_length=50, unique=True)
    enabled = models.BooleanField(default=True)
    input_index = models.CharField(max_length=255, db_index=True)
    input_document_kind = models.CharField(
        max_length=20,
        choices=INPUT_DOCUMENT_KIND_CHOICES,
    )
    default_document_type = models.CharField(
        max_length=30,
        choices=DOCUMENT_TYPE_CHOICES,
    )
    infer_document_type_from_payload = models.BooleanField(default=False)
    deduplicate_scielo = models.BooleanField(default=False)
    openalex_index = models.CharField(
        max_length=255,
        default=settings.ETL_OPENALEX_MATCH_INDEX,
    )
    rules = models.JSONField(default=dict, blank=True)

    objects = EtlPipelineConfigManager()

    panels = [
        FieldPanel("name"),
        FieldPanel("enabled"),
        FieldPanel("input_index"),
        FieldPanel("input_document_kind"),
        FieldPanel("default_document_type"),
        FieldPanel("infer_document_type_from_payload"),
        FieldPanel("deduplicate_scielo"),
        FieldPanel("openalex_index"),
        FieldPanel(
            "rules",
            widget=JSONEditorWidget(options={"mode": "code", "modes": ["code", "tree"]}),
        ),
    ]

    class Meta:
        verbose_name = _("ETL Pipeline Config")
        verbose_name_plural = _("ETL Pipeline Configs")

    def __str__(self):
        return self.name

    def matches_input_index(self, source_index: str) -> bool:
        return fnmatch(source_index, self.input_index)

    def document_type_for_payload(self, source_payload: dict) -> str:
        if not self.infer_document_type_from_payload:
            return self.default_document_type

        payload = clean_source_payload(source_payload)
        raw_type = payload.get("type") or self.default_document_type
        return normalize_document_type_for_etl(raw_type)

    def can_process_payload(self, source_payload):
        if not self.infer_document_type_from_payload:
            return True

        payload_type = self.document_type_for_payload(source_payload)
        if payload_type == normalize_document_type_for_etl(self.default_document_type):
            return True

        return self.input_document_kind == "article"

    def openalex_index_for(self, override: str | None = None) -> str:
        return override or self.openalex_index or settings.ETL_OPENALEX_MATCH_INDEX

    def input_document_class(self):
        input_document_classes = {
            "article": SciELOArticleInputDocument,
            "book": SciELOBookInputDocument,
            "preprint": SciELOPreprintInputDocument,
            "dataset": SciELODatasetInputDocument,
        }

        try:
            return input_document_classes[self.input_document_kind]
        except KeyError as exc:
            raise ValueError(
                f"Invalid input_document_kind for ETL pipeline config '{self.name}': "
                f"{self.input_document_kind}"
            ) from exc

    def clean(self):
        super().clean()
        self.default_document_type = normalize_document_type_for_etl(self.default_document_type)
        self._validate_rules()

    def _validate_rules(self):
        rules = self.rules or {}
        allowed_scielo = {"doi", "pid", "fuzzy"}
        allowed_openalex = {"doi", "isbn", "title"}

        unknown_scielo = set(rules.get("scielo_dedup_strategies", [])) - allowed_scielo
        unknown_openalex = set(rules.get("openalex_match_strategies", [])) - allowed_openalex
        errors = {}
        if unknown_scielo:
            errors["rules"] = [
                f"Invalid scielo_dedup_strategies: {', '.join(sorted(unknown_scielo))}"
            ]
        if unknown_openalex:
            errors.setdefault("rules", []).append(
                f"Invalid openalex_match_strategies: {', '.join(sorted(unknown_openalex))}"
            )
        if errors:
            raise ValidationError(errors)

    def to_rules(self) -> dict:
        self.clean()
        rules = self.rules or {}
        oa_val = rules.get("openalex_validation", {})
        oa_query = rules.get("openalex_query", {})
        return {
            "document_type": normalize_document_type_for_etl(self.default_document_type),
            "scielo_dedup_strategies": list(rules.get("scielo_dedup_strategies", [])),
            "scielo_dedup_allowed_types": list(
                rules.get("scielo_dedup_allowed_types") or []
            ),
            "openalex_match_strategies": list(rules.get("openalex_match_strategies", [])),
            "doi_requires_title_overlap": rules.get("doi_requires_title_overlap", True),
            "doi_requires_year_match": rules.get("doi_requires_year_match", True),
            "doi_requires_source_match": rules.get("doi_requires_source_match", True),
            "pid_requires_year_match": rules.get("pid_requires_year_match", True),
            "pid_requires_source_match": rules.get("pid_requires_source_match", False),
            "pid_requires_title_overlap": rules.get("pid_requires_title_overlap", True),
            "fuzzy_min_similarity": rules.get("fuzzy_min_similarity", 0.85),
            "fuzzy_year_tolerance": rules.get("fuzzy_year_tolerance", 1),
            "fuzzy_requires_source_match": rules.get("fuzzy_requires_source_match", False),
            "openalex_validation": {
                **DEFAULT_OPENALEX_VALIDATION_RULES,
                **oa_val,
            },
            "openalex_query": {
                **DEFAULT_OPENALEX_QUERY_RULES,
                **oa_query,
            },
        }


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

    def mark_success(self, result=EtlResult.UPDATED, has_openalex_match=False, has_scielo_dedup=False, scielo_dedup_ids=None, openalex_match_ids=None, status=EtlStatus.SUCCESS, error=None):
        self.status = status
        self.result = result
        self.has_openalex_match = has_openalex_match
        self.has_scielo_dedup = has_scielo_dedup
        self.scielo_dedup_ids = scielo_dedup_ids or []
        self.openalex_match_ids = openalex_match_ids or []
        self.error = error
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
