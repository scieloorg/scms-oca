import environ

_env = environ.Env()

URL_API_CROSSREF = _env.str(
    "API_CROSSREF",
    default="https://api.crossref.org/works",
)
