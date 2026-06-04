from search_gateway.filter_ui import build_data_source_form_payload


def build_config_fields(data_source, form_key, applied_filters):
    payload = build_data_source_form_payload(
        data_source,
        form_key=form_key,
        applied_filters=applied_filters,
    )
    groups = data_source.get_form_panel_groups(form_key)

    if not groups:
        groups = [
            str(group.get("key") or "").strip()
            for group in (payload or {}).get("form_groups", [])
            if any(str(field.get("kind") or "").strip() == "control" for field in (group.get("fields") or []))
        ]

    normalized_groups = {str(group).strip() for group in (groups or []) if str(group).strip()}
    fields = []
    seen = set()

    for group in (payload or {}).get("form_groups", []):
        if str(group.get("key") or "").strip() not in normalized_groups:
            continue

        for field in group.get("fields", []):
            name = str(field.get("name") or "").strip()
            if name and name not in seen:
                seen.add(name)
                fields.append(field)

    return fields
