from django.conf import settings


VALID_CATEGORY_LEVELS = {"domain", "field", "subfield", "topic"}
ALLOWED_RANKING_METRICS = {
    "journal_impact_cohort",
    "journal_impact_cohort_window_2y",
    "journal_impact_cohort_window_3y",
    "journal_impact_cohort_window_5y",
    "journal_citations_total",
    "journal_citations_mean",
    "journal_citations_mean_window_2y",
    "journal_citations_mean_window_3y",
    "journal_citations_mean_window_5y",
    "journal_publications_count",
    "top_1pct_all_time_publications_share_pct",
    "top_5pct_all_time_publications_share_pct",
    "top_10pct_all_time_publications_share_pct",
    "top_50pct_all_time_publications_share_pct",
}
DEFAULT_CATEGORY_ID = settings.JOURNAL_METRICS_DEFAULT_CATEGORY_ID
DEFAULT_CATEGORY_LEVEL = settings.JOURNAL_METRICS_DEFAULT_CATEGORY_LEVEL
DEFAULT_PUBLICATION_YEAR = settings.JOURNAL_METRICS_DEFAULT_PUBLICATION_YEAR
DEFAULT_MINIMUM_PUBLICATIONS = settings.JOURNAL_METRICS_DEFAULT_MINIMUM_PUBLICATIONS
DEFAULT_RANKING_METRIC = settings.JOURNAL_METRICS_DEFAULT_RANKING_METRIC

FIELD_ALIASES = {
    "country": "journal_country",
    "publisher_name": "journal_publisher",
    "collection": "scielo_collection",
    "collection_name": "scielo_collection_name",
    "collection_acronym": "scielo_collection_acronym",
}

SOURCE_FIELDS = [
    "journal_id",
    "journal_title",
    "journal_issn",
    "journal_publisher",
    "journal_country",
    "scielo_collection",
    "scielo_collection_name",
    "scielo_collection_acronym",
    "category_id",
    "category_level",
    "publication_year",
    "journal_publications_count",
    "journal_citations_total",
    "journal_citations_mean",
    "journal_citations_mean_window_2y",
    "journal_citations_mean_window_3y",
    "journal_citations_mean_window_5y",
    "journal_impact_cohort",
    "journal_impact_cohort_window_2y",
    "journal_impact_cohort_window_3y",
    "journal_impact_cohort_window_5y",
    "top_1pct_all_time_publications_share_pct",
    "top_5pct_all_time_publications_share_pct",
    "top_10pct_all_time_publications_share_pct",
    "top_50pct_all_time_publications_share_pct",
    "is_scielo",
    "is_scopus",
    "is_wos",
    "is_doaj",
    "is_openalex",
    "is_journal_multilingual",
    "is_journal_oa",
]


def normalize_ranking_metric(metric):
    metric_key = str(metric or "").strip()
    return metric_key if metric_key in ALLOWED_RANKING_METRICS else DEFAULT_RANKING_METRIC


def get_index_field_name(field_name):
    return FIELD_ALIASES.get(field_name, field_name)


def normalize_category_level(category_level):
    value = str(category_level or "").strip().lower()
    if not value or value not in VALID_CATEGORY_LEVELS:
        return DEFAULT_CATEGORY_LEVEL
    return value


def normalize_minimum_publications(value):
    if value in (None, ""):
        return None

    try:
        normalized_value = int(value)
    except (TypeError, ValueError):
        return None

    return normalized_value if normalized_value >= 1 else None
