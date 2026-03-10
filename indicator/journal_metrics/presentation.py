from django.http import QueryDict
from django.utils import formats
from django.utils.translation import gettext as _

from . import params
from .config import DEFAULT_PUBLICATION_YEAR, normalize_category_level


def build_ranking_context(applied_filters, ranking_data):
    ranking_configuration = {}
    display_applied_filters = {}

    for key, value in (applied_filters or {}).items():
        target = ranking_configuration if key in params.RANKING_CONFIGURATION_KEYS else display_applied_filters
        target[key] = value

    if ranking_data:
        passthrough_filters = {
            key: value
            for key, value in (applied_filters or {}).items()
            if key not in params.PROFILE_NON_FILTER_KEYS and value not in (None, "")
        }
        ranking_publication_year = ranking_data.get("year") or applied_filters.get("publication_year")

        for entry in ranking_data.get("journals", []):
            journal_issn = str(entry.get("issn") or "").strip()
            if not params.looks_like_issn(journal_issn):
                entry["profile_url"] = ""
                continue

            query_params = QueryDict("", mutable=True)
            for key, value in passthrough_filters.items():
                query_params[key] = str(value)

            for key, value in (
                ("collection", entry.get("collection")),
                ("category_id", entry.get("category_id") or ranking_configuration.get("category_id")),
                ("category_level", entry.get("category_level") or ranking_configuration.get("category_level")),
                ("publication_year", ranking_publication_year),
            ):
                if value not in (None, "") and key not in query_params:
                    query_params[key] = str(value)

            entry["profile_url"] = params.build_profile_url(query_params, journal_issn)

    return {
        "ranking_configuration": ranking_configuration,
        "display_applied_filters": display_applied_filters,
    }


def build_profile_context(
    *,
    journal_issn,
    profile_data,
    selected_category_level,
    selected_category_id,
    selected_publication_year,
    profile_passthrough_filters,
    filters_data,
    filters_error=None,
    profile_error=None,
):
    resolved_category_level = normalize_category_level(selected_category_level)
    resolved_category_id = str(selected_category_id or "").strip()
    resolved_publication_year = str(selected_publication_year or DEFAULT_PUBLICATION_YEAR).strip()

    journal_title = ""
    selected_year_metrics = {}
    profile_year_options = [resolved_publication_year] if resolved_publication_year else []
    profile_category_options = [resolved_category_id] if resolved_category_id else []

    if profile_data:
        journal_title = str(profile_data.get("journal_title") or "").strip()
        resolved_category_level = (
            str(profile_data.get("selected_category_level") or "").strip() or resolved_category_level
        )
        resolved_category_id = (
            str(profile_data.get("selected_category_id") or "").strip() or resolved_category_id
        )
        available_years = [str(year).strip() for year in (profile_data.get("years") or []) if str(year).strip()]
        if available_years and resolved_publication_year not in available_years:
            resolved_publication_year = str(profile_data.get("latest_year") or available_years[-1]).strip()

        selected_year_metrics = next(
            (
                snapshot
                for snapshot in (profile_data.get("annual_snapshots") or [])
                if str(snapshot.get("publication_year") or "").strip() == resolved_publication_year
            ),
            profile_data.get("latest_year_metrics") or {},
        )
        profile_year_options = list(reversed(available_years))
        profile_category_options = profile_data.get("available_categories") or []

    collection_display_value = _build_collection_display_value(profile_data, selected_year_metrics)
    profile_header_attributes = _build_profile_header_attributes(
        journal_issn,
        collection_display_value,
        profile_data,
        selected_year_metrics,
    )

    if not profile_data and journal_issn:
        profile_header_attributes = [{"label": _("ISSN"), "value": journal_issn}]

    profile_kpis = []
    profile_badges = {"attributes": [], "indexing": []}
    if profile_data:
        profile_kpis = [
            {
                "label": _("Publications"),
                "value": _format_metric_value(selected_year_metrics.get("journal_publications_count")),
            },
            {
                "label": _("Total Citations"),
                "value": _format_metric_value(selected_year_metrics.get("journal_citations_total")),
            },
            {
                "label": _("Mean Citations"),
                "value": _format_metric_value(selected_year_metrics.get("journal_citations_mean"), decimal_pos=1),
            },
            {
                "label": _("Cohort Impact (Total)"),
                "value": _format_metric_value(selected_year_metrics.get("journal_impact_cohort"), decimal_pos=1),
            },
            {
                "label": _("Top 10% Share"),
                "value": _format_metric_value(
                    selected_year_metrics.get("top_10pct_all_time_publications_share_pct"),
                    decimal_pos=1,
                    is_percent=True,
                ),
            },
        ]
        profile_badges = {
            "attributes": [
                {"label": _("Is Open Access"), "active": bool(selected_year_metrics.get("is_journal_oa"))},
                {"label": _("Is Multilingual"), "active": bool(selected_year_metrics.get("is_journal_multilingual"))},
            ],
            "indexing": [
                {"label": "SciELO", "active": bool(selected_year_metrics.get("is_scielo"))},
                {"label": "Scopus", "active": bool(selected_year_metrics.get("is_scopus"))},
                {"label": "WoS", "active": bool(selected_year_metrics.get("is_wos"))},
                {"label": "DOAJ", "active": bool(selected_year_metrics.get("is_doaj"))},
                {"label": "OpenAlex", "active": bool(selected_year_metrics.get("is_openalex"))},
            ],
        }

    context = {
        "journal_issn": journal_issn,
        "journal_title": journal_title,
        "selected_category_id": resolved_category_id,
        "selected_category_level": resolved_category_level,
        "selected_publication_year": resolved_publication_year,
        "profile_passthrough_filters": profile_passthrough_filters,
        "profile_data": profile_data,
        "profile_header_attributes": profile_header_attributes,
        "profile_kpis": profile_kpis,
        "profile_badges": profile_badges,
        "profile_year_options": profile_year_options,
        "profile_category_options": profile_category_options,
        "filters_data": filters_data or {},
    }

    if filters_error:
        context["filters_error"] = _("Error loading filters: %s") % filters_error
    if profile_error:
        context["error"] = _("Error executing search: %s") % profile_error

    return context


def _build_collection_display_value(profile_data, selected_year_metrics):
    collection_name = str(
        selected_year_metrics.get("collection_name")
        or (profile_data or {}).get("collection_name")
        or ""
    ).strip()
    collection_acronym = str(
        selected_year_metrics.get("collection_acronym")
        or (profile_data or {}).get("collection_acronym")
        or ""
    ).strip()
    collection_code = str(
        selected_year_metrics.get("collection")
        or (profile_data or {}).get("collection")
        or ""
    ).strip()

    if collection_name and collection_acronym:
        return f"{collection_name} ({collection_acronym})"
    if collection_name and collection_code and collection_name.lower() != collection_code.lower():
        return f"{collection_name} ({collection_code})"
    return collection_name or collection_acronym or collection_code


def _build_profile_header_attributes(journal_issn, collection_display_value, profile_data, selected_year_metrics):
    return [
        attribute
        for attribute in (
            {"label": _("ISSN"), "value": journal_issn},
            {"label": _("SciELO Collection"), "value": collection_display_value},
            {
                "label": _("Country"),
                "value": selected_year_metrics.get("country") or (profile_data or {}).get("country"),
            },
            {
                "label": _("Publisher"),
                "value": selected_year_metrics.get("publisher_name") or (profile_data or {}).get("publisher_name"),
            },
        )
        if str(attribute.get("value") or "").strip()
    ]


def _format_metric_value(value, decimal_pos=0, is_percent=False):
    if value in (None, ""):
        return "-"

    try:
        numeric_value = float(value)
    except (TypeError, ValueError):
        return "-"

    if decimal_pos == 0:
        numeric_value = int(round(numeric_value))

    formatted_value = formats.number_format(
        numeric_value,
        decimal_pos=decimal_pos,
        use_l10n=True,
        force_grouping=True,
    )
    return f"{formatted_value}%" if is_percent else formatted_value
