def parse_global_hits(hits, ranking_metric=None, publication_year=None):
    """Convert raw OpenSearch hits into the ranking_data dict used by templates."""
    journals = []
    for hit in hits:
        src = hit.get("_source", {})
        journals.append({
            "title": src.get("journal_title"),
            "issn": src.get("journal_issn"),
            "country": src.get("journal_country"),
            "publisher_name": src.get("journal_publisher"),
            "is_journal_oa": src.get("is_journal_oa_global"),
            "publication_year": src.get("publication_year", publication_year),
            "global_field_normalized_impact": src.get("global_field_normalized_impact"),
            "global_field_normalized_impact_median": src.get("global_field_normalized_impact_median"),
            "global_consistency_score": src.get("global_consistency_score"),
            "global_total_publications": src.get("global_total_publications"),
            "global_total_citations": src.get("global_total_citations"),
            "global_num_observations": src.get("global_num_observations"),
        })

    return {
        "ranking_metric": ranking_metric,
        "year": publication_year,
        "journals": journals,
    }
