from django.urls import resolve, reverse

from indicator import views


def test_journal_metrics_canonical_url():
    path = reverse("indicator_journal_metrics")

    assert path == "/indicators/journal-metrics/"
    assert resolve(path).func == views.journal_metrics_view
