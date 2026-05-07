from dataclasses import dataclass, field
from fnmatch import fnmatch
from typing import Literal

from django.conf import settings

from harvest.utils import clean_source_payload

DocumentType = Literal["article", "preprint", "dataset", "book", "book-chapter"]
DedupStrategy = Literal["doi", "pid", "fuzzy"]
OpenAlexStrategy = Literal["doi", "isbn", "title"]
MergeAction = Literal["prefer_scielo", "union", "openalex_if_missing", "max", "sum"]


@dataclass(frozen=True)
class OpenAlexValidationRules:
    year_tolerance: int
    require_openalex_year: bool
    require_source_match: bool
    source_similarity_threshold: float
    title_match_threshold: float
    title_reject_threshold: float
    min_score: int
    strict_min_score: int
    doi_score: int = 50
    year_exact_score: int = 30
    year_close_score: int = 20
    isbn_score: int = 35
    source_id_score: int = 40
    source_title_score: int = 30
    title_score: int = 30
    isbn_requires_title_match: bool = False
    isbn_title_threshold: float = 0.80


@dataclass(frozen=True)
class MergeRules:
    field_actions: dict[str, MergeAction] = field(default_factory=dict)
    scielo_is_base: bool = True


@dataclass(frozen=True)
class DocumentRules:
    document_type: DocumentType
    scielo_dedup_strategies: tuple[DedupStrategy, ...]
    openalex_match_strategies: tuple[OpenAlexStrategy, ...]
    doi_requires_title_overlap: bool
    pid_requires_year_match: bool
    pid_requires_source_match: bool
    pid_requires_title_overlap: bool
    fuzzy_min_similarity: float
    fuzzy_year_tolerance: int
    fuzzy_requires_source_match: bool
    openalex_validation: OpenAlexValidationRules
    merge: MergeRules


DEFAULT_MERGE_RULES = MergeRules(
    field_actions={
        "citation_count": "sum",
        "topics": "openalex_if_missing",
        "referenced_works": "union",
        "authorships": "prefer_scielo",
        "institutions": "prefer_scielo",
        "author_country_codes": "union",
        "metrics": "union",
    }
)

DEFAULT_OPENALEX_VALIDATION = OpenAlexValidationRules(
    year_tolerance=1,
    require_openalex_year=True,
    require_source_match=False,
    source_similarity_threshold=0.80,
    title_match_threshold=0.85,
    title_reject_threshold=0.80,
    min_score=50,
    strict_min_score=60,
)


def article_rules() -> DocumentRules:
    return DocumentRules(
        document_type="article",
        scielo_dedup_strategies=("doi", "pid", "fuzzy"),
        openalex_match_strategies=("doi", "isbn", "title"),
        doi_requires_title_overlap=True,
        pid_requires_year_match=True,
        pid_requires_source_match=True,
        pid_requires_title_overlap=True,
        fuzzy_min_similarity=0.85,
        fuzzy_year_tolerance=1,
        fuzzy_requires_source_match=True,
        openalex_validation=DEFAULT_OPENALEX_VALIDATION,
        merge=DEFAULT_MERGE_RULES,
    )


def dataset_rules() -> DocumentRules:
    return DocumentRules(
        document_type="dataset",
        scielo_dedup_strategies=("doi", "pid"),
        openalex_match_strategies=("doi",),
        doi_requires_title_overlap=True,
        pid_requires_year_match=True,
        pid_requires_source_match=False,
        pid_requires_title_overlap=True,
        fuzzy_min_similarity=0.95,
        fuzzy_year_tolerance=0,
        fuzzy_requires_source_match=False,
        openalex_validation=OpenAlexValidationRules(
            year_tolerance=1,
            require_openalex_year=True,
            require_source_match=False,
            source_similarity_threshold=0.80,
            title_match_threshold=0.90,
            title_reject_threshold=0.85,
            min_score=60,
            strict_min_score=70,
        ),
        merge=DEFAULT_MERGE_RULES,
    )


def preprint_rules() -> DocumentRules:
    return DocumentRules(
        document_type="preprint",
        scielo_dedup_strategies=("doi", "pid", "fuzzy"),
        openalex_match_strategies=("doi", "title"),
        doi_requires_title_overlap=True,
        pid_requires_year_match=True,
        pid_requires_source_match=False,
        pid_requires_title_overlap=True,
        fuzzy_min_similarity=0.88,
        fuzzy_year_tolerance=1,
        fuzzy_requires_source_match=False,
        openalex_validation=OpenAlexValidationRules(
            year_tolerance=1,
            require_openalex_year=True,
            require_source_match=False,
            source_similarity_threshold=0.80,
            title_match_threshold=0.88,
            title_reject_threshold=0.82,
            min_score=50,
            strict_min_score=60,
        ),
        merge=DEFAULT_MERGE_RULES,
    )


def book_rules() -> DocumentRules:
    return DocumentRules(
        document_type="book",
        scielo_dedup_strategies=("doi", "pid", "fuzzy"),
        openalex_match_strategies=("doi", "isbn", "title"),
        doi_requires_title_overlap=True,
        pid_requires_year_match=True,
        pid_requires_source_match=False,
        pid_requires_title_overlap=True,
        fuzzy_min_similarity=0.88,
        fuzzy_year_tolerance=1,
        fuzzy_requires_source_match=False,
        openalex_validation=DEFAULT_OPENALEX_VALIDATION,
        merge=DEFAULT_MERGE_RULES,
    )


def book_chapter_rules() -> DocumentRules:
    return DocumentRules(
        document_type="book-chapter",
        scielo_dedup_strategies=("doi", "pid", "fuzzy"),
        openalex_match_strategies=("doi", "isbn", "title"),
        doi_requires_title_overlap=True,
        pid_requires_year_match=True,
        pid_requires_source_match=False,
        pid_requires_title_overlap=True,
        fuzzy_min_similarity=0.90,
        fuzzy_year_tolerance=1,
        fuzzy_requires_source_match=False,
        openalex_validation=OpenAlexValidationRules(
            year_tolerance=1,
            require_openalex_year=True,
            require_source_match=False,
            source_similarity_threshold=0.80,
            title_match_threshold=0.85,
            title_reject_threshold=0.80,
            min_score=50,
            strict_min_score=60,
            isbn_requires_title_match=True,
            isbn_title_threshold=0.80,
        ),
        merge=DEFAULT_MERGE_RULES,
    )


@dataclass(frozen=True)
class PipelineTarget:
    document_type: str
    bronze_index: str
    silver_index_pattern: str
    rules: DocumentRules

    def matches_bronze_index(self, source_index: str) -> bool:
        return fnmatch(source_index, self.bronze_index)

    def document_type_for(self, source_payload: dict) -> str:
        payload = clean_source_payload(source_payload)
        raw_type = (
            payload.get("type")
            if self.document_type in {"article", "book"}
            else self.document_type
        ) or self.document_type

        return str(raw_type).strip().lower().replace("_", "-")


PIPELINE_TARGETS = {
    "article": PipelineTarget(
        document_type="article",
        bronze_index=settings.ETL_BRONZE_SCIELO_ARTICLES,
        silver_index_pattern=settings.ETL_SILVER_ARTICLE_PATTERN,
        rules=article_rules(),
    ),
    "book": PipelineTarget(
        document_type="book",
        bronze_index=settings.ETL_BRONZE_SCIELO_BOOKS,
        silver_index_pattern=settings.ETL_SILVER_BOOK,
        rules=book_rules(),
    ),
    "preprint": PipelineTarget(
        document_type="preprint",
        bronze_index=settings.ETL_BRONZE_SCIELO_PREPRINT,
        silver_index_pattern=settings.ETL_SILVER_PREPRINT,
        rules=preprint_rules(),
    ),
    "dataset": PipelineTarget(
        document_type="dataset",
        bronze_index=settings.ETL_BRONZE_SCIELO_DATASET,
        silver_index_pattern=settings.ETL_SILVER_DATASET,
        rules=dataset_rules(),
    ),
}


def resolve_target_name(source_index: str) -> str | None:
    for name, target in PIPELINE_TARGETS.items():
        if target.matches_bronze_index(source_index):
            return name
    return None


def get_pipeline_target(source_index: str) -> PipelineTarget:
    target_name = resolve_target_name(source_index)
    if not target_name:
        raise ValueError(f"No ETL target configured for source index: {source_index}")
    return PIPELINE_TARGETS[target_name]


def resolve_target_names(target_type: str) -> list[str]:
    if target_type == "all":
        return list(PIPELINE_TARGETS.keys())
    if target_type not in PIPELINE_TARGETS:
        raise ValueError(f"Unknown ETL target type: {target_type}")
    return [target_type]


__all__ = [
    "DocumentType",
    "DedupStrategy",
    "OpenAlexStrategy",
    "MergeAction",
    "OpenAlexValidationRules",
    "MergeRules",
    "DocumentRules",
    "DEFAULT_MERGE_RULES",
    "DEFAULT_OPENALEX_VALIDATION",
    "article_rules",
    "dataset_rules",
    "preprint_rules",
    "book_rules",
    "book_chapter_rules",
    "PipelineTarget",
    "PIPELINE_TARGETS",
    "resolve_target_name",
    "get_pipeline_target",
    "resolve_target_names",
]
