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


def parse_indicator_response(res, breakdown_variable):
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
