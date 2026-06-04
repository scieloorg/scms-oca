import warnings
warnings.warn(
    "indicator.scripts is deprecated.",
    DeprecationWarning,
    stacklevel=2
)
from indicator import scheduler


def run():
    scheduler.delete_tasks()
