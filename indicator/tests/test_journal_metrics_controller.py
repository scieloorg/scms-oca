from django.conf import settings

if not settings.configured:
    settings.configure(
        OP_INDEX_ALL_BRONZE="bronze_*",
        OP_INDEX_SCI_PROD="bronze_*",
        OP_INDEX_SOC_PROD="bronze_social_production",
        OPENSEARCH_INDEX_JOURNAL_METRICS="journal_metrics_*",
        JOURNAL_METRICS_DEFAULT_CATEGORY_ID="Social Sciences",
        JOURNAL_METRICS_DEFAULT_CATEGORY_LEVEL="field",
        JOURNAL_METRICS_DEFAULT_MINIMUM_PUBLICATIONS=50,
        JOURNAL_METRICS_DEFAULT_PUBLICATION_YEAR="2020",
        JOURNAL_METRICS_DEFAULT_RANKING_METRIC="journal_impact_cohort_window_3y",
        USE_I18N=False,
    )

from indicator.journal_metrics import config as journal_metrics_config
from indicator.journal_metrics import params as journal_metrics_params
from indicator.journal_metrics import presentation as journal_metrics_presentation
from indicator.search import controller as search_controller


class DummyOpenSearchClient:
    def __init__(self):
        self.calls = []

    def search(self, index, body):
        self.calls.append({"index": index, "body": body})
        return {
            "hits": {"hits": []},
            "aggregations": {"unique_journals": {"value": 0}},
        }


def _patch_journal_metrics_dependencies(monkeypatch, client):
    monkeypatch.setattr(search_controller, "get_opensearch_client", lambda: client)
    monkeypatch.setattr(
        search_controller.data_sources_with_settings,
        "get_data_source",
        lambda _data_source: {
            "index_name": "journal_metrics_*",
            "field_settings": {
                "category_id": {"index_field_name": "category_id"},
                "category_level": {"index_field_name": "category_level"},
            },
        },
    )
    monkeypatch.setattr(
        search_controller.data_sources_with_settings,
        "get_query_operator_fields",
        lambda _data_source: set(),
    )
    monkeypatch.setattr(
        search_controller.data_sources_with_settings,
        "get_index_field_name_to_filter_name_map",
        lambda _data_source: {
            "category_id": "category_id",
            "category_level": "category_level",
        },
    )


def test_get_journal_metrics_data_defaults_to_social_sciences_with_default_minimum_publications(monkeypatch):
    client = DummyOpenSearchClient()
    _patch_journal_metrics_dependencies(monkeypatch, client)

    ranking_data, error = search_controller.get_journal_metrics_data({})

    assert error is None
    assert ranking_data["year"] == journal_metrics_config.DEFAULT_PUBLICATION_YEAR

    must_clauses = client.calls[0]["body"]["query"]["bool"]["must"]

    assert {"term": {"category_level": "field"}} in must_clauses
    assert {"term": {"category_id": journal_metrics_config.DEFAULT_CATEGORY_ID}} in must_clauses
    assert {
        "range": {
            "journal_publications_count": {
                "gte": journal_metrics_config.DEFAULT_MINIMUM_PUBLICATIONS
            }
        }
    } in must_clauses


def test_get_journal_metrics_data_applies_minimum_publications_filter(monkeypatch):
    client = DummyOpenSearchClient()
    _patch_journal_metrics_dependencies(monkeypatch, client)

    ranking_data, error = search_controller.get_journal_metrics_data(
        {
            "category_level": "field",
            "minimum_publications": "10",
        }
    )

    assert error is None
    must_clauses = client.calls[0]["body"]["query"]["bool"]["must"]

    assert {"term": {"category_level": "field"}} in must_clauses
    assert {"term": {"category_id": journal_metrics_config.DEFAULT_CATEGORY_ID}} not in must_clauses
    assert {"range": {"journal_publications_count": {"gte": 10}}} in must_clauses


def test_normalize_journal_metrics_request_filters_applies_defaults():
    normalized_filters = journal_metrics_params.normalize_request_filters(
        {},
        source_filters={},
        clean=True,
    )

    assert normalized_filters["category_level"] == journal_metrics_config.DEFAULT_CATEGORY_LEVEL
    assert normalized_filters["category_id"] == journal_metrics_config.DEFAULT_CATEGORY_ID
    assert normalized_filters["minimum_publications"] == str(journal_metrics_config.DEFAULT_MINIMUM_PUBLICATIONS)


def test_build_journal_metrics_profile_context_uses_profile_data_defaults():
    profile_context = journal_metrics_presentation.build_profile_context(
        journal_issn="1234-5678",
        profile_data={
            "journal_title": "Journal A",
            "journal_issn": "1234-5678",
            "selected_category_level": "topic",
            "selected_category_id": "Health",
            "years": ["2020", "2021"],
            "latest_year": "2021",
            "latest_year_metrics": {"publication_year": "2021", "country": "Brazil"},
            "available_categories": ["Health", "Policy"],
        },
        selected_category_level="field",
        selected_category_id="Social Sciences",
        selected_publication_year="2019",
        profile_passthrough_filters={},
        filters_data={},
    )

    assert profile_context["journal_title"] == "Journal A"
    assert profile_context["selected_category_level"] == "topic"
    assert profile_context["selected_category_id"] == "Health"
    assert profile_context["selected_publication_year"] == "2021"
    assert profile_context["profile_year_options"] == ["2021", "2020"]
    assert profile_context["profile_category_options"] == ["Health", "Policy"]
