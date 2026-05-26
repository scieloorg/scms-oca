import environ

_env = environ.Env()

URL_API_OPENALEX_INSTITUTIONS = _env.str(
    "URL_API_OPENALEX_INSTITUTIONS",
    default="https://api.openalex.org/institutions",
)
