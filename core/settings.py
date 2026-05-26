import environ

_env = environ.Env()

DIRECTORY_DEFAULT_CONTRIBUTOR = _env.str(
    "DIRECTORY_DEFAULT_CONTRIBUTOR",
    default="SciELO",
)
DIRECTORY_IMPORT_DELIMITER = _env.str(
    "DIRECTORY_IMPORT_DELIMITER",
    default=",",
)
