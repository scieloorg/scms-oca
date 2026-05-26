import environ

_env = environ.Env()

# Global metrics upload settings
GLOBAL_METRICS_FILE_UPLOAD_OPENSEARCH_INDEX = _env.str(
    "GLOBAL_METRICS_FILE_UPLOAD_OPENSEARCH_INDEX",
    default="global_metrics_upload_file",
)
GLOBAL_METRICS_FILE_UPLOAD_BULK_CHUNK_SIZE = _env.int(
    "GLOBAL_METRICS_FILE_UPLOAD_BULK_CHUNK_SIZE",
    default=100,
)
GLOBAL_METRICS_UPLOAD_ERROR_INDEX = _env.str(
    "GLOBAL_METRICS_UPLOAD_ERROR_INDEX",
    default="global_metrics_upload_errors",
)

# OpenSearch raw index names
OS_INDEX_RAW_PREPRINT = _env.str(
    "OS_INDEX_RAW_PREPRINT",
    default="raw_scielo_preprint",
)
OS_INDEX_RAW_BOOK = _env.str(
    "OS_INDEX_RAW_BOOK",
    default="raw_scielo_book",
)
OS_INDEX_RAW_SCIELO_DATA_DATASET = _env.str(
    "OS_INDEX_RAW_SCIELO_DATA_DATASET",
    default="raw_scielo_data_dataset",
)
OS_INDEX_RAW_SCIELO_DATA_DATAVERSE = _env.str(
    "OS_INDEX_RAW_SCIELO_DATA_DATAVERSE",
    default="raw_scielo_data_comunities_dataverse",
)
OS_INDEX_RAW_SCIELO_DATA = _env.str(
    "OS_INDEX_RAW_SCIELO_DATA",
    default="raw_scielo_data",
)

# Harvest books, preprint, and SciELO Data settings
SCIELO_BOOKS_BASE_URL = _env("SCIELO_BOOKS_BASE_URL", default=None)
SITE_SCIELO_DATA = _env("SITE_SCIELO_DATA", default="https://data.scielo.org")
USER_AGENT = _env(
    "USER_AGENT",
    default=(
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    ),
)
ENDPOINT_OAI_PMH_PREPRINT = _env(
    "ENDPOINT_OAI_PMH_PREPRINT",
    default="https://preprints.scielo.org/index.php/scielo/oai",
)
