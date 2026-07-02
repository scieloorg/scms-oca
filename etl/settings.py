import environ

_env = environ.Env()

# ETL settings
ETL_PUBLIC_ALIAS = _env.str(
    "ETL_PUBLIC_ALIAS",
    default="silver_scientific_production",
)
ETL_ERROR_INDEX = _env.str("ETL_ERROR_INDEX", default="etl_errors")
ETL_DEFAULT_BATCH_SIZE = _env.int("ETL_DEFAULT_BATCH_SIZE", default=5000)
ETL_DB_CONNECTION_REFRESH_INTERVAL = _env.int(
    "ETL_DB_CONNECTION_REFRESH_INTERVAL",
    default=100,
)
ETL_DOCUMENT_TYPE_ALIAS = _env.json(
    "ETL_DOCUMENT_TYPE_ALIAS",
    default={
        "research-article": "article",
        "review": "article",
        "review-article": "article",
        "abstract": "article",
        "addendum": "article",
        "article-commentary": "article",
        "book-review": "article",
        "brief-report": "article",
        "case-report": "article",
        "letter": "article",
        "editorial": "article",
        "correction": "article",
        "erratum": "article",
        "news": "article",
        "oration": "article",
        "press-release": "article",
        "rapid-communication": "article",
        "undefined": "article",
        "book-part": "book-chapter",
        "chapter": "book-chapter",
    },
)
ETL_OPENACCESS_STATUSES = _env.json(
    "ETL_OPENACCESS_STATUSES",
    default={
        "gold",
        "green",
        "hybrid",
        "bronze",
        "closed",
        "diamond",
    },
)

# ETL bronze index names
ETL_INPUT_SCIELO_ARTICLES = _env.str(
    "ETL_INPUT_SCIELO_ARTICLES",
    default="bronze_scielo_articles-000001",
)
ETL_INPUT_SCIELO_BOOKS = _env.str(
    "ETL_INPUT_SCIELO_BOOKS",
    default="bronze_scielo_books",
)
ETL_INPUT_SCIELO_PREPRINT = _env.str(
    "ETL_INPUT_SCIELO_PREPRINT",
    default="bronze_scielo_preprint",
)
ETL_INPUT_SCIELO_DATASET = _env.str(
    "ETL_INPUT_SCIELO_DATASET",
    default="bronze_scielo_dataset",
)
ETL_INPUT_OPENALEX_WORKS = _env.str(
    "ETL_INPUT_OPENALEX_WORKS",
    default="raw_openalex_works",
)
ETL_OPENALEX_MATCH_INDEX = _env.str(
    "ETL_OPENALEX_MATCH_INDEX",
    default="silver_openalex-*",
)

# ETL silver index pattern
ETL_SILVER_INDEX_PATTERN = _env.str(
    "ETL_SILVER_INDEX_PATTERN",
    default="silver_scientific_production",
)
ETL_SILVER_WRITE_ALIAS = _env.str(
    "ETL_SILVER_WRITE_ALIAS",
    default="silver_write",
)
ETL_SILVER_ROLLOVER_MAX_SIZE = _env.str(
    "ETL_SILVER_ROLLOVER_MAX_SIZE",
    default="30gb",
)

# ETL OpenAlex-only backfill
ETL_OPENALEX_ONLY_INDEX_PATTERN = _env.str(
    "ETL_OPENALEX_ONLY_INDEX_PATTERN",
    default="silver_openalex",
)
ETL_OPENALEX_ONLY_WRITE_ALIAS = _env.str(
    "ETL_OPENALEX_ONLY_WRITE_ALIAS",
    default="silver_openalex_write",
)
