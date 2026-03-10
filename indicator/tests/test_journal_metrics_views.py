from urllib.parse import parse_qs, urlparse

from django.http import HttpResponse
from django.test import RequestFactory

from indicator import views


def test_journal_metrics_view_renders_profile_for_canonical_query_route(monkeypatch):
    request = RequestFactory().get(
        "/indicators/journal-metrics/",
        {"journal": "1234-5678", "collection": "scl", "publication_year": "2020"},
    )
    captured = {}

    def fake_render_profile(request, issn=None):
        captured["issn"] = issn
        return HttpResponse("profile")

    monkeypatch.setattr(views, "_render_journal_metrics_profile", fake_render_profile)

    response = views.journal_metrics_view(request)

    assert response.status_code == 200
    assert response.content == b"profile"
    assert captured == {"issn": "1234-5678"}

def test_journal_metrics_profile_redirect_helper_strips_journal_params():
    request = RequestFactory().get(
        "/indicators/journal-metrics/",
        {
            "collection": "scl",
            "category_level": "field",
            "journal": "1234-5678",
            "journal_title": "Journal A",
        },
    )

    redirect_url = views.journal_metrics_params.build_profile_url(
        request.GET,
        "1234-5678",
    )

    parsed = urlparse(redirect_url)
    assert parse_qs(parsed.query) == {
        "journal": ["1234-5678"],
        "collection": ["scl"],
        "category_level": ["field"],
    }
    assert parsed.path == "/indicators/journal-metrics/"


def test_journal_metrics_profile_url_orders_canonical_query_params():
    request = RequestFactory().get(
        "/indicators/journal-metrics/",
        {
            "journal": "1234-5678",
            "category_id": "Social Sciences",
            "publication_year": "2024",
            "collection": "scl",
            "category_level": "field",
        },
    )

    redirect_url = views.journal_metrics_params.build_profile_url(request.GET, "1234-5678")

    assert redirect_url == (
        "/indicators/journal-metrics/"
        "?journal=1234-5678&collection=scl&publication_year=2024"
        "&category_level=field&category_id=Social+Sciences"
    )

def test_root_journal_metrics_redirect_view_uses_canonical_query_route():
    request = RequestFactory().get(
        "/",
        {"journal": "1234-5678", "collection": "scl", "publication_year": "2024"},
    )

    response = views.root_journal_metrics_redirect_view(request)

    parsed = urlparse(response["Location"])
    assert response.status_code == 302
    assert parsed.path == "/indicators/journal-metrics/"
    assert parse_qs(parsed.query) == {
        "journal": ["1234-5678"],
        "collection": ["scl"],
        "publication_year": ["2024"],
    }


def test_journal_metrics_timeseries_view_treats_journal_query_as_issn(monkeypatch):
    request = RequestFactory().get(
        "/indicators/journal-metrics/timeseries/",
        {
            "journal": "1234-5678",
            "journal_title": "Journal A",
            "collection": "scl",
            "category_level": "field",
            "publication_year": "2020",
        },
    )
    captured = {}

    def fake_get_journal_metrics_timeseries(**kwargs):
        captured.update(kwargs)
        return {"ok": True}, None

    monkeypatch.setattr(
        views.search_controller,
        "get_journal_metrics_timeseries",
        fake_get_journal_metrics_timeseries,
    )

    response = views.journal_metrics_timeseries_view(request)

    assert response.status_code == 200
    assert captured["issn"] == "1234-5678"
    assert captured["journal"] is None
    assert captured["form_filters"] == {"collection": "scl"}
