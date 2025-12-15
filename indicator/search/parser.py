from . import utils


def parse_journal_metrics_response(response, selected_year=None, ranking_metric=None):
    if not selected_year:
        selected_year = "2024"
    if not ranking_metric:
        ranking_metric = "cwts_snip"

    hits = response.get("hits", {}).get("hits", [])
    journals = []
    for hit in hits:
        source = hit.get("_source", {})
        yearly_info = source.get("yearly_info", {}).get(selected_year, {})
        journal = {
            "title": source.get("journal", "Unknown"),
            "issns": source.get("issns", []),
            "cwts_snip": yearly_info.get("cwts_snip", 0),
            "doaj_num_docs": yearly_info.get("doaj_num_docs", 0),
            "openalex_docs_2024_5": yearly_info.get("openalex_docs_2024_5", 0),
            "scielo_num_docs": yearly_info.get("scielo_num_docs", 0),
            "scimago_best_quartile": yearly_info.get("scimago_best_quartile", 0),
            "scimago_cites_by_doc_2_years": yearly_info.get("scimago_cites_by_doc_2_years", 0),
            "scimago_estimated_apc": yearly_info.get("scimago_estimated_apc", 0),
            "scimago_estimated_value": yearly_info.get("scimago_estimated_value", 0),
            "scimago_female_authors_percent": yearly_info.get("scimago_female_authors_percent", 0),
            "scimago_overton": yearly_info.get("scimago_overton", 0),
            "scimago_sdg": yearly_info.get("scimago_sdg", 0),
            "scimago_sjr": yearly_info.get("scimago_sjr", 0),
            "scimago_total_cites_3_years": yearly_info.get("scimago_total_cites_3_years", 0),
            "scimago_total_docs": yearly_info.get("scimago_total_docs", 0)
        }
        journals.append(journal)

    journals.sort(key=lambda x: x[ranking_metric], reverse=True)

    return {
        "journals": journals,
        "total_journals": len(journals),
        "year": selected_year,
    }


def parse_journal_metrics_timeseries(source):
    yearly_info = source.get("yearly_info", {}) or {}

    def _is_year_key(k):
        try:
            year_int = int(k)
        except (TypeError, ValueError):
            return False
        return 1500 <= year_int <= 3000

    years = sorted([str(k) for k in yearly_info.keys() if _is_year_key(k)], key=lambda x: int(x))

    ndocs_per_year = []
    total_citations_per_year = []
    citations_per_doc_per_year = []

    for year in years:
        info = yearly_info.get(year, {}) or {}
        ndocs = info.get("scimago_total_docs", 0) or 0
        citations = info.get("scimago_total_cites_3_years", 0) or 0
        cpd = info.get("scimago_cites_by_doc_2_years")
        if cpd is None:
            cpd = (citations / ndocs) if ndocs else 0

        ndocs_per_year.append(int(ndocs) if isinstance(ndocs, (int, float)) else 0)
        total_citations_per_year.append(int(citations) if isinstance(citations, (int, float)) else 0)
        citations_per_doc_per_year.append(float(cpd) if isinstance(cpd, (int, float)) else 0)

    return {
        "journal": source.get("journal"),
        "issns": source.get("issns", []),
        "years": years,
        "ndocs_per_year": ndocs_per_year,
        "total_citations_per_year": total_citations_per_year,
        "citations_per_doc_per_year": citations_per_doc_per_year,
        "metrics_source": {
            "docs": "yearly_info.<year>.scimago_total_docs",
            "citations": "yearly_info.<year>.scimago_total_cites_3_years",
            "citations_per_doc": "yearly_info.<year>.scimago_cites_by_doc_2_years",
        },
    }


def parse_indicator_response(res, breakdown_variable, study_unit="document"):
    if study_unit not in ("document", "journal"):
        study_unit = "document"
    aggs = res.get("aggregations", {})
    per_year_buckets = aggs.get("per_year", {}).get("buckets", [])
    
    years = [str(b["key"]) for b in per_year_buckets]
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
        
        series_ndocs = []
        series_citations = []

        for breakdown in breakdown_keys:
            data_ndocs = []
            data_citations = []
            for year_bucket in per_year_buckets:
                found = False
                for b in year_bucket.get("breakdown", {}).get("buckets", []):
                    if str(b["key"]) == breakdown:
                        data_ndocs.append(b["doc_count"])
                        data_citations.append(int(b.get("total_citations", {}).get("value", 0)))
                        found = True
                        break
                if not found:
                    data_ndocs.append(0)
                    data_citations.append(0)
            
            series_ndocs.append({"name": breakdown, "data": data_ndocs, "type": "documents"})
            series_citations.append({"name": breakdown, "data": data_citations, "type": "citations"})

        # Combine series for documents and citations
        series = series_ndocs + series_citations
        
        # Standardize breakdown keys and series names
        standardized_breakdown_keys = utils.standardize_breakdown_keys(breakdown_keys, series)
        
        # Append "(Documents)" or "(Citations)" after standardization
        for s in series:
            if s.get("type") == "documents":
                s["name"] = f"{s['name']} (Documents)"
            elif s.get("type") == "citations":
                s["name"] = f"{s['name']} (Citations)"
            s.pop("type", None) # Remove the temporary type field

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
