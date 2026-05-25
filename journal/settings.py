import environ

_env = environ.Env()

URL_API_OPENALEX_JOURNALS = _env.str(
    "URL_API_OPENALEX_JOURNALS",
    default="https://api.openalex.org/sources",
)

