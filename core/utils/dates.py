from datetime import datetime, timezone as dt_timezone


def epoch_ms_to_datetime(raw):
    if not raw:
        return None

    return datetime.fromtimestamp(float(raw) / 1000.0, tz=dt_timezone.utc)
