from django import template
from django.utils.translation import gettext as _

register = template.Library()


@register.filter
def stz_filter(value):
    if not value:
        return value
    
    # Convert boolean strings to Yes/No
    if str(value).lower() == 'true':
        return 'Yes'
    elif str(value).lower() == 'false':
        return 'No'
    
    # Words that should remain in UPPERCASE
    uppercase_words = {
        'cwts', 'sjr', 'snip', 'issn', 'apc', 'usd', 'sdg', 'doi', 'api', 'url', 'id'
    }
    
    # Words that should remain in lowercase (prepositions, articles, conjunctions)
    lowercase_words = {
        # English
        'a', 'an', 'and', 'as', 'at', 'but', 'by', 'for', 'from', 'in', 
        'into', 'of', 'on', 'or', 'the', 'to', 'with', 'is', 'are', 'vs',
        # Portuguese
        'o', 'a', 'os', 'as', 'um', 'uma', 'uns', 'umas',
        'do', 'da', 'dos', 'das', 'de', 'em', 'no', 'na', 'nos', 'nas',
        'ao', 'à', 'aos', 'às', 'por', 'para', 'com', 'sem', 'sob', 'sobre'
    }
    
    # Replace underscores with spaces
    words = value.replace('_', ' ').split()
    
    # Apply casing rules
    result = []

    for i, word in enumerate(words):
        word_lower = word.lower()
        
        # First word is always capitalized (unless it's an acronym)
        if i == 0:
            if word_lower in uppercase_words:
                result.append(word.upper())
            else:
                result.append(word.capitalize())

        # Check if word should be uppercase (acronyms)
        elif word_lower in uppercase_words:
            result.append(word.upper())

        # Check if word should be lowercase (prepositions)
        elif word_lower in lowercase_words:
            result.append(word_lower)

        # Capitalize other words
        else:
            result.append(word.capitalize())
    
    return ' '.join(result)


@register.filter
def get_attr(obj, attr_name):
    if obj is None or not attr_name:
        return None
    if isinstance(obj, dict):
        return obj.get(attr_name)
    return getattr(obj, attr_name, None)


@register.filter
def ui_label(field_key):
    """Map known filter keys to translated UI labels (Journal Metrics + Indicators)."""
    if not field_key:
        return field_key

    key = str(field_key).strip()
    mapping = {
        "publication_year": _("Publication Year"),
        "year": _("Publication Year"),
        "ranking_metric": _("Ranking metric"),
        "limit": _("Number of results"),
        "journal_title": _("Journal"),
        "journal_issn": _("ISSN"),
        "publisher_name": _("Publisher"),
        "publisher": _("Publisher"),
        "country": _("Country"),
        "collection": _("Collection"),
        "category_level": _("Category Type"),
        "category_id": _("Category"),
        "scope": _("Scope"),
        "source_index_open_alex": _("Indexed in"),
        "source_type": _("Source Type"),
        "source_name": _("Source"),
        "funder": _("Funder"),
    }

    return mapping.get(key, stz_filter(key))


@register.filter
def ui_value(value, field_key=None):
    """Translate known coded values for a given field."""
    if value is None:
        return value

    raw = str(value).strip()

    # Common boolean strings.
    if raw.lower() == "true":
        return _("Yes")
    if raw.lower() == "false":
        return _("No")

    if not field_key:
        return stz_filter(raw)

    key = str(field_key).strip()

    if key in ("ranking_metric", "metric"):
        # Journal Metrics ranking metric codes -> translated labels.
        metric_key = raw.strip()
        mapping = {
            "journal_impact_normalized": _("Cohort Impact (Total)"),
            "journal_impact_normalized_window_2y": _("Cohort Impact (2 years)"),
            "journal_impact_normalized_window_3y": _("Cohort Impact (3 years)"),
            "journal_impact_normalized_window_5y": _("Cohort Impact (5 years)"),
            "journal_citations_total": _("Total Citations"),
            "journal_citations_mean": _("Mean Citations"),
            "journal_citations_mean_window_2y": _("Mean Citations (2 years)"),
            "journal_citations_mean_window_3y": _("Mean Citations (3 years)"),
            "journal_citations_mean_window_5y": _("Mean Citations (5 years)"),
            "journal_publications_count": _("Publication Count"),
        }
        if metric_key in mapping:
            return mapping[metric_key]

    if key in ("category_level", "category_type"):
        mapping = {
            "domain": _("Domain"),
            "field": _("Field"),
            "subfield": _("Subfield"),
            "topic": _("Topic"),
        }
        return mapping.get(raw.lower(), stz_filter(raw))

    return stz_filter(raw)
