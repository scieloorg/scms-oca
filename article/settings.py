import environ

_env = environ.Env()

URL_API_OPENALEX = _env.str(
    "API_OPENALEX",
    default="https://api.openalex.org/works",
)
