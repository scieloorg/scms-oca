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

from indicator.search import parser, query
from indicator.journal_metrics.config import get_index_field_name, normalize_ranking_metric


def test_journal_metrics_config_uses_cohort_metric_names():
    assert normalize_ranking_metric("journal_impact_cohort_window_3y") == "journal_impact_cohort_window_3y"
    assert get_index_field_name("journal_impact_cohort_window_3y") == "journal_impact_cohort_window_3y"
    assert get_index_field_name("country") == "journal_country"


def test_build_journal_metrics_body_sorts_by_new_index_field():
    body = query.build_journal_metrics_body(ranking_metric="journal_impact_cohort_window_3y")

    assert body["sort"] == [
        {"journal_impact_cohort_window_3y": {"order": "desc", "missing": "_last"}}
    ]


def test_parse_journal_metrics_response_maps_new_schema_fields():
    response = {
        "hits": {
            "hits": [
                {
                    "_source": {
                        "journal_id": "S1",
                        "journal_title": "Journal A",
                        "journal_issn": "1234-5678",
                        "journal_publisher": "Publisher A",
                        "journal_country": "Brazil",
                        "scielo_collection": "br",
                        "scielo_collection_name": "Brazil",
                        "scielo_collection_acronym": "SciELO Brasil",
                        "category_id": "Medicine",
                        "category_level": "field",
                        "publication_year": 2024,
                        "journal_publications_count": 12,
                        "journal_citations_total": 88,
                        "journal_citations_mean": 7.3,
                        "journal_citations_mean_window_2y": 5.5,
                        "journal_citations_mean_window_3y": 6.1,
                        "journal_citations_mean_window_5y": 6.9,
                        "journal_impact_cohort": 1.2,
                        "journal_impact_cohort_window_2y": 1.4,
                        "journal_impact_cohort_window_3y": 1.8,
                        "journal_impact_cohort_window_5y": 2.1,
                        "top_10pct_all_time_publications_share_pct": 25.0,
                        "is_scielo": True,
                        "is_scopus": True,
                        "is_wos": False,
                        "is_doaj": True,
                        "is_openalex": True,
                        "is_journal_multilingual": False,
                        "is_journal_oa": True,
                    }
                }
            ]
        },
        "aggregations": {"unique_journals": {"value": 1}},
    }

    parsed = parser.parse_journal_metrics_response(
        response,
        selected_year=2024,
        ranking_metric="journal_impact_cohort_window_3y",
    )

    assert parsed["ranking_metric"] == "journal_impact_cohort_window_3y"
    assert parsed["year"] == 2024

    entry = parsed["journals"][0]
    assert entry["publisher_name"] == "Publisher A"
    assert entry["country"] == "Brazil"
    assert entry["collection"] == "br"
    assert entry["collection_name"] == "Brazil"
    assert entry["collection_acronym"] == "SciELO Brasil"
    assert entry["journal_impact_cohort"] == 1.2
    assert entry["journal_impact_cohort_window_3y"] == 1.8
    assert entry["is_journal_oa"] is True


def test_parse_journal_metrics_timeseries_maps_new_schema_fields():
    hits = [
        {
            "_source": {
                "journal_id": "S1",
                "journal_title": "Journal A",
                "journal_issn": "1234-5678",
                "journal_publisher": "Publisher A",
                "journal_country": "Brazil",
                "scielo_collection": "br",
                "scielo_collection_name": "Brazil",
                "scielo_collection_acronym": "SciELO Brasil",
                "category_id": "Medicine",
                "category_level": "field",
                "publication_year": 2023,
                "journal_publications_count": 10,
                "journal_citations_total": 60,
                "journal_citations_mean": 6.0,
                "journal_citations_mean_window_2y": 4.5,
                "journal_citations_mean_window_3y": 5.0,
                "journal_citations_mean_window_5y": 5.4,
                "journal_impact_cohort": 1.1,
                "journal_impact_cohort_window_2y": 1.2,
                "journal_impact_cohort_window_3y": 1.3,
                "journal_impact_cohort_window_5y": 1.4,
                "top_10pct_all_time_publications_share_pct": 20.0,
                "is_journal_oa": False,
            }
        },
        {
            "_source": {
                "journal_id": "S1",
                "journal_title": "Journal A",
                "journal_issn": "1234-5678",
                "journal_publisher": "Publisher A",
                "journal_country": "Brazil",
                "scielo_collection": "br",
                "scielo_collection_name": "Brazil",
                "scielo_collection_acronym": "SciELO Brasil",
                "category_id": "Medicine",
                "category_level": "field",
                "publication_year": 2024,
                "journal_publications_count": 12,
                "journal_citations_total": 88,
                "journal_citations_mean": 7.3,
                "journal_citations_mean_window_2y": 5.5,
                "journal_citations_mean_window_3y": 6.1,
                "journal_citations_mean_window_5y": 6.9,
                "journal_impact_cohort": 1.2,
                "journal_impact_cohort_window_2y": 1.4,
                "journal_impact_cohort_window_3y": 1.8,
                "journal_impact_cohort_window_5y": 2.1,
                "top_10pct_all_time_publications_share_pct": 25.0,
                "is_journal_oa": True,
            }
        },
    ]

    parsed = parser.parse_journal_metrics_timeseries(hits)

    assert parsed["publisher_name"] == "Publisher A"
    assert parsed["country"] == "Brazil"
    assert parsed["collection"] == "br"
    assert parsed["collection_name"] == "Brazil"
    assert parsed["collection_acronym"] == "SciELO Brasil"
    assert parsed["journal_impact_cohort_window_5y_per_year"] == [1.4, 2.1]
    assert parsed["latest_year_metrics"]["is_journal_oa"] is True
