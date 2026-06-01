import warnings
warnings.warn(
    "indicator.scripts is deprecated.",
    DeprecationWarning,
    stacklevel=2
)
from indicator.models import Indicator


def run():
    Indicator.delete()
