from django.utils import timezone


def epoch_ms_to_datetime(raw):
    if not raw:
        return None

    return timezone.datetime.fromtimestamp(float(raw) / 1000.0, tz=timezone.utc)
