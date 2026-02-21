from . import utils


def parse_journal_metrics_response(response, selected_year=None, ranking_metric=None):
    if not ranking_metric:
        ranking_metric = "journal_impact_normalized"

    def _to_float(value, fallback=0.0):
        try:
            return float(value)
        except (TypeError, ValueError):
            return fallback

    def _to_int(value, fallback=0):
        try:
            return int(value)
        except (TypeError, ValueError):
            return fallback

    hits = response.get("hits", {}).get("hits", [])
    journals = []
    for hit in hits:
        source = hit.get("_source", {})
        journal = {
            "journal_id": source.get("journal_id"),
            "title": source.get("journal_title", "Unknown"),
            "issn": source.get("journal_issn", ""),
            "publisher_name": source.get("publisher_name", ""),
            "country": source.get("country", ""),
            "collection": source.get("collection", ""),
            "category_id": source.get("category_id", ""),
            "category_level": source.get("category_level", ""),
            "publication_year": _to_int(source.get("publication_year")),
            "journal_publications_count": _to_int(source.get("journal_publications_count")),
            "journal_citations_total": _to_float(source.get("journal_citations_total")),
            "journal_citations_mean": _to_float(source.get("journal_citations_mean")),
            "journal_citations_mean_window_2y": _to_float(source.get("journal_citations_mean_window_2y")),
            "journal_citations_mean_window_3y": _to_float(source.get("journal_citations_mean_window_3y")),
            "journal_citations_mean_window_5y": _to_float(source.get("journal_citations_mean_window_5y")),
            "journal_impact_normalized": _to_float(source.get("journal_impact_normalized")),
            "journal_impact_normalized_window_2y": _to_float(source.get("journal_impact_normalized_window_2y")),
            "journal_impact_normalized_window_3y": _to_float(source.get("journal_impact_normalized_window_3y")),
            "journal_impact_normalized_window_5y": _to_float(source.get("journal_impact_normalized_window_5y")),
            "top_1pct_all_time_publications_share_pct": _to_float(
                source.get("top_1pct_all_time_publications_share_pct")
            ),
            "top_5pct_all_time_publications_share_pct": _to_float(
                source.get("top_5pct_all_time_publications_share_pct")
            ),
            "top_10pct_all_time_publications_share_pct": _to_float(
                source.get("top_10pct_all_time_publications_share_pct")
            ),
            "top_50pct_all_time_publications_share_pct": _to_float(
                source.get("top_50pct_all_time_publications_share_pct")
            ),
            "is_scielo": bool(source.get("is_scielo", False)),
            "is_scopus": bool(source.get("is_scopus", False)),
            "is_wos": bool(source.get("is_wos", False)),
            "is_doaj": bool(source.get("is_doaj", False)),
            "is_openalex": bool(source.get("is_openalex", False)),
            "is_journal_multilingual": bool(source.get("is_journal_multilingual", False)),
        }
        journals.append(journal)

    journals.sort(key=lambda item: _to_float(item.get(ranking_metric)), reverse=True)

    unique_journals = int(
        response.get("aggregations", {}).get("unique_journals", {}).get("value", len(journals))
    )

    return {
        "journals": journals,
        "total_journals": unique_journals,
        "returned_journals": len(journals),
        "year": selected_year,
        "ranking_metric": ranking_metric,
    }


def parse_journal_metrics_timeseries(hits):
    if not hits:
        return {
            "journal_title": None,
            "journal_issn": None,
            "years": [],
            "journal_publications_count_per_year": [],
            "journal_citations_total_per_year": [],
            "journal_citations_mean_per_year": [],
            "journal_impact_normalized_per_year": [],
            "top_1pct_all_time_publications_share_pct_per_year": [],
            "top_5pct_all_time_publications_share_pct_per_year": [],
            "top_10pct_all_time_publications_share_pct_per_year": [],
            "top_50pct_all_time_publications_share_pct_per_year": [],
            "latest_year": None,
            "latest_year_metrics": {},
            "annual_snapshots": [],
        }

    def _to_int(value, fallback=0):
        try:
            return int(value)
        except (TypeError, ValueError):
            return fallback

    def _to_float(value, fallback=0.0):
        try:
            return float(value)
        except (TypeError, ValueError):
            return fallback

    snapshots = []
    for hit in hits:
        source = hit.get("_source", {})
        snapshots.append({
            "publication_year": _to_int(source.get("publication_year")),
            "journal_publications_count": _to_int(source.get("journal_publications_count")),
            "journal_citations_total": _to_float(source.get("journal_citations_total")),
            "journal_citations_mean": _to_float(source.get("journal_citations_mean")),
            "journal_citations_mean_window_2y": _to_float(source.get("journal_citations_mean_window_2y")),
            "journal_citations_mean_window_3y": _to_float(source.get("journal_citations_mean_window_3y")),
            "journal_citations_mean_window_5y": _to_float(source.get("journal_citations_mean_window_5y")),
            "journal_impact_normalized": _to_float(source.get("journal_impact_normalized")),
            "journal_impact_normalized_window_2y": _to_float(source.get("journal_impact_normalized_window_2y")),
            "journal_impact_normalized_window_3y": _to_float(source.get("journal_impact_normalized_window_3y")),
            "journal_impact_normalized_window_5y": _to_float(source.get("journal_impact_normalized_window_5y")),
            "top_1pct_all_time_publications_share_pct": _to_float(
                source.get("top_1pct_all_time_publications_share_pct")
            ),
            "top_5pct_all_time_publications_share_pct": _to_float(
                source.get("top_5pct_all_time_publications_share_pct")
            ),
            "top_10pct_all_time_publications_share_pct": _to_float(
                source.get("top_10pct_all_time_publications_share_pct")
            ),
            "top_50pct_all_time_publications_share_pct": _to_float(
                source.get("top_50pct_all_time_publications_share_pct")
            ),
            "is_scielo": bool(source.get("is_scielo", False)),
            "is_scopus": bool(source.get("is_scopus", False)),
            "is_wos": bool(source.get("is_wos", False)),
            "is_doaj": bool(source.get("is_doaj", False)),
            "is_openalex": bool(source.get("is_openalex", False)),
            "is_journal_multilingual": bool(source.get("is_journal_multilingual", False)),
            "category_id": source.get("category_id"),
            "category_level": source.get("category_level"),
            "publisher_name": source.get("publisher_name"),
            "country": source.get("country"),
            "collection": source.get("collection"),
        })

    snapshots = sorted(snapshots, key=lambda item: item["publication_year"])

    years = [str(item["publication_year"]) for item in snapshots]
    latest = snapshots[-1] if snapshots else {}
    source0 = hits[0].get("_source", {})

    return {
        "journal_title": source0.get("journal_title"),
        "journal_issn": source0.get("journal_issn"),
        "journal_id": source0.get("journal_id"),
        "publisher_name": latest.get("publisher_name"),
        "country": latest.get("country"),
        "collection": latest.get("collection"),
        "years": years,
        "journal_publications_count_per_year": [item["journal_publications_count"] for item in snapshots],
        "journal_citations_total_per_year": [item["journal_citations_total"] for item in snapshots],
        "journal_citations_mean_per_year": [item["journal_citations_mean"] for item in snapshots],
        "journal_citations_mean_window_2y_per_year": [
            item["journal_citations_mean_window_2y"] for item in snapshots
        ],
        "journal_citations_mean_window_3y_per_year": [
            item["journal_citations_mean_window_3y"] for item in snapshots
        ],
        "journal_citations_mean_window_5y_per_year": [
            item["journal_citations_mean_window_5y"] for item in snapshots
        ],
        "journal_impact_normalized_per_year": [item["journal_impact_normalized"] for item in snapshots],
        "journal_impact_normalized_window_2y_per_year": [
            item["journal_impact_normalized_window_2y"] for item in snapshots
        ],
        "journal_impact_normalized_window_3y_per_year": [
            item["journal_impact_normalized_window_3y"] for item in snapshots
        ],
        "journal_impact_normalized_window_5y_per_year": [
            item["journal_impact_normalized_window_5y"] for item in snapshots
        ],
        "top_1pct_all_time_publications_share_pct_per_year": [
            item["top_1pct_all_time_publications_share_pct"] for item in snapshots
        ],
        "top_5pct_all_time_publications_share_pct_per_year": [
            item["top_5pct_all_time_publications_share_pct"] for item in snapshots
        ],
        "top_10pct_all_time_publications_share_pct_per_year": [
            item["top_10pct_all_time_publications_share_pct"] for item in snapshots
        ],
        "top_50pct_all_time_publications_share_pct_per_year": [
            item["top_50pct_all_time_publications_share_pct"] for item in snapshots
        ],
        "latest_year": latest.get("publication_year"),
        "latest_year_metrics": latest,
        "annual_snapshots": snapshots,
    }


def parse_indicator_response(res, breakdown_variable, study_unit="document"):
    if study_unit not in ("document", "journal"):
        study_unit = "document"
    aggs = res.get("aggregations", {})
    per_year_buckets = aggs.get("per_year", {}).get("buckets", [])
    
    years = [str(b.get("key_as_string") or b.get("key")) for b in per_year_buckets]
    ndocs_per_year = [b["doc_count"] for b in per_year_buckets]
    total_citations_per_year = [int(b.get("total_citations", {}).get("value", 0)) for b in per_year_buckets]

    data = {
        "years": years,
        "ndocs_per_year": ndocs_per_year,
        "total_citations_per_year": total_citations_per_year,
    }

    # If the query included a filter agg for cited docs, expose it for both modes.
    has_docs_with_citations = any("docs_with_citations" in b for b in per_year_buckets)
    if has_docs_with_citations:
        docs_with_citations_per_year = [
            int((b.get("docs_with_citations", {}) or {}).get("doc_count", 0)) for b in per_year_buckets
        ]
        percent_docs_with_citations_per_year = []
        for total_docs, cited_docs in zip(ndocs_per_year, docs_with_citations_per_year):
            percent_docs_with_citations_per_year.append(round((cited_docs / total_docs) * 100, 2) if total_docs else 0)

        data["docs_with_citations_per_year"] = docs_with_citations_per_year
        data["percent_docs_with_citations_per_year"] = percent_docs_with_citations_per_year

    if study_unit == "journal":
        nperiodicals_per_year = [int(b.get("unique_periodicals", {}).get("value", 0)) for b in per_year_buckets]
        docs_with_citations_per_year = data.get("docs_with_citations_per_year") or [
            int((b.get("docs_with_citations", {}) or {}).get("doc_count", 0)) for b in per_year_buckets
        ]

        periodicals_with_cited_docs_per_year = []
        for b in per_year_buckets:
            docs_with_citations_bucket = b.get("docs_with_citations", {}) or {}
            periodicals_with_cited_docs_per_year.append(
                int(docs_with_citations_bucket.get("unique_periodicals", {}).get("value", 0))
            )

        docs_per_periodical_per_year = []
        citations_per_periodical_per_year = []
        cited_docs_per_periodical_per_year = []
        percent_periodicals_with_cited_docs_per_year = []

        for ndocs, citations, nperiodicals, cited_docs, cited_periodicals in zip(
            ndocs_per_year,
            total_citations_per_year,
            nperiodicals_per_year,
            docs_with_citations_per_year,
            periodicals_with_cited_docs_per_year,
        ):
            if nperiodicals:
                docs_per_periodical_per_year.append(round(ndocs / nperiodicals, 4))
                citations_per_periodical_per_year.append(round(citations / nperiodicals, 4))
                cited_docs_per_periodical_per_year.append(round(cited_docs / nperiodicals, 4))
                percent_periodicals_with_cited_docs_per_year.append(round((cited_periodicals / nperiodicals) * 100, 2))
            else:
                docs_per_periodical_per_year.append(0)
                citations_per_periodical_per_year.append(0)
                cited_docs_per_periodical_per_year.append(0)
                percent_periodicals_with_cited_docs_per_year.append(0)

        data["nperiodicals_per_year"] = nperiodicals_per_year
        data["periodicals_with_cited_docs_per_year"] = periodicals_with_cited_docs_per_year
        data["docs_per_periodical_per_year"] = docs_per_periodical_per_year
        data["citations_per_periodical_per_year"] = citations_per_periodical_per_year
        data["cited_docs_per_periodical_per_year"] = cited_docs_per_periodical_per_year
        data["percent_periodicals_with_cited_docs_per_year"] = percent_periodicals_with_cited_docs_per_year

    if breakdown_variable:
        data["breakdown_variable"] = breakdown_variable

        breakdown_keys_set = set()
        for year_bucket in per_year_buckets:
            for b in year_bucket.get("breakdown", {}).get("buckets", []):
                breakdown_keys_set.add(str(b["key"]))

        breakdown_keys = sorted(list(breakdown_keys_set))

        if study_unit == "journal":
            series_periodicals = []
            series_docs_per_periodical = []
            series_citations_per_periodical = []
            series_cited_docs_per_periodical = []
            series_pct_periodicals_with_cited_docs = []

            for breakdown in breakdown_keys:
                data_periodicals = []
                data_docs_per_periodical = []
                data_citations_per_periodical = []
                data_cited_docs_per_periodical = []
                data_pct_periodicals_with_cited_docs = []

                for year_bucket in per_year_buckets:
                    bucket = None
                    for b in year_bucket.get("breakdown", {}).get("buckets", []):
                        if str(b["key"]) == breakdown:
                            bucket = b
                            break

                    if bucket is None:
                        data_periodicals.append(0)
                        data_docs_per_periodical.append(0)
                        data_citations_per_periodical.append(0)
                        data_cited_docs_per_periodical.append(0)
                        data_pct_periodicals_with_cited_docs.append(0)
                        continue

                    nperiodicals = int((bucket.get("unique_periodicals", {}) or {}).get("value", 0))
                    ndocs = int(bucket.get("doc_count", 0))
                    citations = int((bucket.get("total_citations", {}) or {}).get("value", 0))
                    docs_with_citations_bucket = bucket.get("docs_with_citations", {}) or {}
                    cited_docs = int(docs_with_citations_bucket.get("doc_count", 0))
                    cited_periodicals = int(
                        (docs_with_citations_bucket.get("unique_periodicals", {}) or {}).get("value", 0)
                    )

                    data_periodicals.append(nperiodicals)
                    if nperiodicals:
                        data_docs_per_periodical.append(round(ndocs / nperiodicals, 4))
                        data_citations_per_periodical.append(round(citations / nperiodicals, 4))
                        data_cited_docs_per_periodical.append(round(cited_docs / nperiodicals, 4))
                        data_pct_periodicals_with_cited_docs.append(
                            round((cited_periodicals / nperiodicals) * 100, 2)
                        )
                    else:
                        data_docs_per_periodical.append(0)
                        data_citations_per_periodical.append(0)
                        data_cited_docs_per_periodical.append(0)
                        data_pct_periodicals_with_cited_docs.append(0)

                series_periodicals.append({"name": breakdown, "data": data_periodicals, "type": "periodicals"})
                series_docs_per_periodical.append(
                    {"name": breakdown, "data": data_docs_per_periodical, "type": "documents_per_periodical"}
                )
                series_citations_per_periodical.append(
                    {"name": breakdown, "data": data_citations_per_periodical, "type": "citations_per_periodical"}
                )
                series_cited_docs_per_periodical.append(
                    {"name": breakdown, "data": data_cited_docs_per_periodical, "type": "cited_docs_per_periodical"}
                )
                series_pct_periodicals_with_cited_docs.append(
                    {
                        "name": breakdown,
                        "data": data_pct_periodicals_with_cited_docs,
                        "type": "pct_periodicals_with_cited_docs",
                    }
                )

            series = (
                series_periodicals
                + series_docs_per_periodical
                + series_citations_per_periodical
                + series_cited_docs_per_periodical
                + series_pct_periodicals_with_cited_docs
            )
        else:
            series_ndocs = []
            series_citations = []
            series_cited_docs = []
            series_pct_cited_docs = []

            for breakdown in breakdown_keys:
                data_ndocs = []
                data_citations = []
                data_cited_docs = []
                data_pct_cited_docs = []
                for year_bucket in per_year_buckets:
                    found = False
                    for b in year_bucket.get("breakdown", {}).get("buckets", []):
                        if str(b["key"]) == breakdown:
                            data_ndocs.append(b["doc_count"])
                            data_citations.append(int(b.get("total_citations", {}).get("value", 0)))
                            cited_docs_count = int((b.get("docs_with_citations", {}) or {}).get("doc_count", 0))
                            data_cited_docs.append(cited_docs_count)
                            data_pct_cited_docs.append(
                                round((cited_docs_count / b["doc_count"]) * 100, 2) if b["doc_count"] else 0
                            )
                            found = True
                            break
                    if not found:
                        data_ndocs.append(0)
                        data_citations.append(0)
                        data_cited_docs.append(0)
                        data_pct_cited_docs.append(0)

                series_ndocs.append({"name": breakdown, "data": data_ndocs, "type": "documents"})
                series_citations.append({"name": breakdown, "data": data_citations, "type": "citations"})
                series_cited_docs.append({"name": breakdown, "data": data_cited_docs, "type": "cited_documents"})
                series_pct_cited_docs.append({"name": breakdown, "data": data_pct_cited_docs, "type": "pct_cited_documents"})

            # Combine series for all breakdown metrics
            series = series_ndocs + series_citations + series_cited_docs + series_pct_cited_docs

        # Standardize breakdown keys and series names
        standardized_breakdown_keys = utils.standardize_breakdown_keys(breakdown_keys, series)

        # Append metric suffixes after standardization
        for s in series:
            if s.get("type") == "documents":
                s["name"] = f"{s['name']} (Documents)"
            elif s.get("type") == "citations":
                s["name"] = f"{s['name']} (Citations)"
            elif s.get("type") == "cited_documents":
                s["name"] = f"{s['name']} (Cited Documents)"
            elif s.get("type") == "pct_cited_documents":
                s["name"] = f"{s['name']} (Percent Docs With Citations)"
            elif s.get("type") == "periodicals":
                s["name"] = f"{s['name']} (Periodicals)"
            elif s.get("type") == "documents_per_periodical":
                s["name"] = f"{s['name']} (Documents per Periodical)"
            elif s.get("type") == "citations_per_periodical":
                s["name"] = f"{s['name']} (Citations per Periodical)"
            elif s.get("type") == "cited_docs_per_periodical":
                s["name"] = f"{s['name']} (Cited Documents per Periodical)"
            elif s.get("type") == "pct_periodicals_with_cited_docs":
                s["name"] = f"{s['name']} (Percent Periodicals With Cited Docs)"
            s.pop("type", None)  # Remove the temporary type field

        data["breakdown_keys"] = standardized_breakdown_keys
        data["series"] = series
    else:
        # If no breakdown, create simple series for documents and citations
        series = [
            {"name": "Documents", "data": ndocs_per_year},
            {"name": "Citations", "data": total_citations_per_year}
        ]
        data["series"] = series

    return data


def _align_series_to_years(reference_years, source_years, source_values):
    if not reference_years:
        return []
    if not source_years or not source_values:
        return [0 for _ in reference_years]

    values_by_year = {}
    for idx, year in enumerate(source_years):
        if idx >= len(source_values):
            continue
        values_by_year[str(year)] = source_values[idx]

    return [values_by_year.get(str(year), 0) for year in reference_years]


def _compute_relative_percent_series(filtered_values, baseline_values, precision=2):
    relative_values = []
    for filtered_value, baseline_value in zip(filtered_values, baseline_values):
        try:
            filtered_number = float(filtered_value)
        except (TypeError, ValueError):
            filtered_number = 0.0
        try:
            baseline_number = float(baseline_value)
        except (TypeError, ValueError):
            baseline_number = 0.0

        if baseline_number <= 0:
            relative_values.append(0.0)
            continue

        relative_values.append(round((filtered_number / baseline_number) * 100, precision))

    return relative_values


def _compute_citations_per_document_series(citations_per_year, docs_per_year):
    values = []
    for citations, docs in zip(citations_per_year, docs_per_year):
        try:
            citations_value = float(citations)
        except (TypeError, ValueError):
            citations_value = 0.0
        try:
            docs_value = float(docs)
        except (TypeError, ValueError):
            docs_value = 0.0
        values.append(round(citations_value / docs_value, 4) if docs_value else 0.0)
    return values


def parse_terms_agg_keys(response, agg_name):
    if not response or not agg_name:
        return []
    buckets = response.get("aggregations", {}).get(agg_name, {}).get("buckets", [])
    return [bucket.get("key") for bucket in buckets if bucket.get("key")]


def parse_category_spider(response, agg_name="by_category", limit=12):
    buckets = response.get("aggregations", {}).get(agg_name, {}).get("buckets", [])
    spider = []

    def _to_int(value, fallback=0):
        try:
            return int(value)
        except (TypeError, ValueError):
            return fallback

    def _to_float(value, fallback=0.0):
        try:
            return float(value)
        except (TypeError, ValueError):
            return fallback

    for bucket in buckets:
        category_key = bucket.get("key")
        if not category_key:
            continue
        publications_total = _to_int((bucket.get("publications_total", {}) or {}).get("value", 0) or 0)
        citations_total = _to_int((bucket.get("citations_total", {}) or {}).get("value", 0) or 0)
        citations_mean = _to_float((bucket.get("citations_mean", {}) or {}).get("value", 0) or 0)
        spider.append(
            {
                "category": category_key,
                "publications_total": publications_total,
                "citations_total": citations_total,
                "citations_mean": citations_mean,
            }
        )

    spider.sort(key=lambda item: item.get("publications_total", 0), reverse=True)
    if limit:
        try:
            limit_int = int(limit)
        except (TypeError, ValueError):
            limit_int = 12
        spider = spider[: max(0, limit_int)]

    return spider


def compute_indicator_relative_metrics(filtered_data, baseline_data, study_unit):
    years = (filtered_data or {}).get("years", [])
    baseline_years = (baseline_data or {}).get("years", [])

    if not years or not baseline_data:
        return {"enabled": False}

    filtered_ndocs = _align_series_to_years(years, filtered_data.get("years", []), filtered_data.get("ndocs_per_year", []))
    baseline_ndocs = _align_series_to_years(years, baseline_years, baseline_data.get("ndocs_per_year", []))

    filtered_total_citations = _align_series_to_years(
        years, filtered_data.get("years", []), filtered_data.get("total_citations_per_year", [])
    )
    baseline_total_citations = _align_series_to_years(
        years, baseline_years, baseline_data.get("total_citations_per_year", [])
    )

    filtered_docs_with_citations = _align_series_to_years(
        years, filtered_data.get("years", []), filtered_data.get("docs_with_citations_per_year", [])
    )
    baseline_docs_with_citations = _align_series_to_years(
        years, baseline_years, baseline_data.get("docs_with_citations_per_year", [])
    )

    filtered_percent_docs_with_citations = _align_series_to_years(
        years, filtered_data.get("years", []), filtered_data.get("percent_docs_with_citations_per_year", [])
    )
    baseline_percent_docs_with_citations = _align_series_to_years(
        years, baseline_years, baseline_data.get("percent_docs_with_citations_per_year", [])
    )

    filtered_citations_per_doc = _compute_citations_per_document_series(filtered_total_citations, filtered_ndocs)
    baseline_citations_per_doc = _compute_citations_per_document_series(baseline_total_citations, baseline_ndocs)

    relative_metrics = {
        "enabled": True,
        "docs_share_pct_per_year": _compute_relative_percent_series(filtered_ndocs, baseline_ndocs),
        "citations_share_pct_per_year": _compute_relative_percent_series(filtered_total_citations, baseline_total_citations),
        "citations_per_doc_share_pct_per_year": _compute_relative_percent_series(filtered_citations_per_doc, baseline_citations_per_doc),
        "cited_docs_share_pct_per_year": _compute_relative_percent_series(filtered_docs_with_citations, baseline_docs_with_citations),
        "pct_docs_with_citations_share_pct_per_year": _compute_relative_percent_series(
            filtered_percent_docs_with_citations, baseline_percent_docs_with_citations
        ),
    }

    if study_unit == "journal":
        filtered_periodicals = _align_series_to_years(
            years, filtered_data.get("years", []), filtered_data.get("nperiodicals_per_year", [])
        )
        baseline_periodicals = _align_series_to_years(
            years, baseline_years, baseline_data.get("nperiodicals_per_year", [])
        )

        filtered_docs_per_source = _align_series_to_years(
            years, filtered_data.get("years", []), filtered_data.get("docs_per_periodical_per_year", [])
        )
        baseline_docs_per_source = _align_series_to_years(
            years, baseline_years, baseline_data.get("docs_per_periodical_per_year", [])
        )

        filtered_citations_per_source = _align_series_to_years(
            years, filtered_data.get("years", []), filtered_data.get("citations_per_periodical_per_year", [])
        )
        baseline_citations_per_source = _align_series_to_years(
            years, baseline_years, baseline_data.get("citations_per_periodical_per_year", [])
        )

        filtered_cited_docs_per_source = _align_series_to_years(
            years, filtered_data.get("years", []), filtered_data.get("cited_docs_per_periodical_per_year", [])
        )
        baseline_cited_docs_per_source = _align_series_to_years(
            years, baseline_years, baseline_data.get("cited_docs_per_periodical_per_year", [])
        )

        filtered_pct_sources_with_cited_docs = _align_series_to_years(
            years,
            filtered_data.get("years", []),
            filtered_data.get("percent_periodicals_with_cited_docs_per_year", []),
        )
        baseline_pct_sources_with_cited_docs = _align_series_to_years(
            years,
            baseline_years,
            baseline_data.get("percent_periodicals_with_cited_docs_per_year", []),
        )

        relative_metrics["periodicals_share_pct_per_year"] = _compute_relative_percent_series(
            filtered_periodicals, baseline_periodicals
        )
        relative_metrics["docs_per_source_share_pct_per_year"] = _compute_relative_percent_series(
            filtered_docs_per_source, baseline_docs_per_source
        )
        relative_metrics["citations_per_source_share_pct_per_year"] = _compute_relative_percent_series(
            filtered_citations_per_source, baseline_citations_per_source
        )
        relative_metrics["cited_docs_per_source_share_pct_per_year"] = _compute_relative_percent_series(
            filtered_cited_docs_per_source, baseline_cited_docs_per_source
        )
        relative_metrics["pct_sources_with_cited_docs_share_pct_per_year"] = _compute_relative_percent_series(
            filtered_pct_sources_with_cited_docs, baseline_pct_sources_with_cited_docs
        )

    return relative_metrics
