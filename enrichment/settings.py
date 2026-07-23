import environ

_env = environ.Env()

WORLD_REGIONS_REQUESTS_PER_SECOND = _env.int(
    "WORLD_REGIONS_REQUESTS_PER_SECOND",
    default=-1,
)
WORLD_REGIONS_SLICES = _env.str(
    "WORLD_REGIONS_SLICES",
    default="auto",
)
WORLD_REGIONS_TASK_POLL_INTERVAL = _env.int(
    "WORLD_REGIONS_TASK_POLL_INTERVAL",
    default=5,
)
