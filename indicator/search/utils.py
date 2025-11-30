from search_gateway.data_sources import  get_aggregation_qualified_field_name


def clean_form_filters(filters_dict):
    """
    Removes empty filters and the CSRF token from a dictionary of form filters.
    """
    cleaned = {k: v for k, v in filters_dict.items() if v}
    cleaned.pop("csrfmiddlewaretoken", None)
    return cleaned


def year_range_to_list(start_year, end_year):
    """
    Converts start and end year to a list of years as strings.
    """
    if start_year and end_year:
        return [str(y) for y in range(int(start_year), int(end_year) + 1)]
    return []


def standardize_breakdown_keys(keys, series):
    """
    Standardizes known breakdown keys for better readability (e.g., "1"/"0" to "Yes"/"No").
    """
    oa_map = {"1": "Yes", "0": "No"}

    # Apply the mapping only if the keys appear to be related to the oa_map.
    # This is more flexible than an exact set match.
    if any(str(k) in oa_map for k in keys):
        return _apply_mapping(keys, series, oa_map)

    # If no keys match, return the original keys, leaving the series unmodified.
    return keys


def standardize_values(values: list, sort=True):
    vals = list(set(str(item).strip() for item in values if item))

    if sort:
        return sorted(vals)

    return vals


def translate_fields(filters, field_settings):
    """
    Translate form field names to Elasticsearch index field names
    based on the provided field settings, applying transformations as needed.
    """
    translated = {}
    searchable = {}

    # A set to keep track of form fields that are handled by a transformation
    # and should not be processed again in the main loop.
    handled_by_transform = set()

    # First, handle fields with special transformations
    for fl_name, fl_settings in field_settings.items():
        transform_type = fl_settings.get("filter", {}).get("transform", {}).get("type")
        if not transform_type:
            continue

        index_field_name = fl_settings.get("index_field_name")
        if not index_field_name:
            continue

        value = None
        if transform_type == "boolean":
            value = transform_boolean_yes_no(filters.get(fl_name))
            handled_by_transform.add(fl_name)

        elif transform_type == "year_range":
            value = transform_year_range(filters, fl_settings)
            # Add the source fields to the handled set
            handled_by_transform.update(fl_settings.get("filter", {}).get("transform", {}).get("sources", []))

        if value is not None:
            translated[fl_name] = {
                "filter_name": fl_name,
                "value": value,
            }

    # Second, handle the rest of the fields (simple name translation)
    for fl_name, value in filters.items():
        # Skip fields that were already processed by a transformation
        if fl_name in handled_by_transform:
            continue

        fl_settings = field_settings.get(fl_name, {})
        index_field_name = fl_settings.get("index_field_name")

        if index_field_name and value:
            translated[fl_name] = {
                "filter_name": fl_name,
                "value": value,
            }

    # Third, handle field type
    for fl_name, data in translated.items():
        index_field_name = field_settings.get(fl_name, {}).get("index_field_name")
        fl_aggr_type = field_settings.get(fl_name, {}).get("filter", {}).get("aggregation_type", "keyword")
        aggegation_qualified_field_name = get_aggregation_qualified_field_name(
            index_field_name,
            fl_aggr_type,
        )
        searchable[aggegation_qualified_field_name] = data.get("value")

    return searchable


def _apply_mapping(keys, series, mapping):
    """
    Applies a mapping to a list of keys and a series list to standardize names.
    """
    for s in series:
        # Use .get() to avoid a KeyError if a name is not in the mapping
        s["name"] = mapping.get(str(s["name"]), s["name"])

    # Also map the keys themselves for consistency
    return [mapping.get(str(k), k) for k in keys]


def _transform_boolean_yes_no(value):
    """
    Transforms a 'Yes'/'No' string to a boolean.
    """
    if value == "Yes":
        return True
    if value == "No":
        return False
    return None


def _transform_year_range(filters, settings):
    """
    Transforms start and end year fields into a list of years.
    """
    source_fields = settings.get("source_fields", [])
    if len(source_fields) != 2:
        return None

    start_year = filters.get(source_fields[0])
    end_year = filters.get(source_fields[1])

    if start_year and end_year:
        return year_range_to_list(start_year, end_year)
    return None
