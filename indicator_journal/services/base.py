def infer_panel_groups_from_payload(payload):
    """Return the keys of form groups that contain at least one control field."""
    panel_groups = []
    for group in (payload or {}).get("form_groups") or []:
        group_key = str(group.get("key") or "").strip()
        if not group_key:
            continue
        if any(
            str(field.get("kind") or "").strip() == "control"
            for field in (group.get("fields") or [])
        ):
            panel_groups.append(group_key)
    return panel_groups


def collect_form_group_fields(payload, group_keys):
    """Return the ordered, deduplicated list of field dicts for the given group keys."""
    selected_fields = []
    selected_names = set()
    normalized_keys = {str(k or "").strip() for k in (group_keys or []) if str(k or "").strip()}

    for group in (payload or {}).get("form_groups") or []:
        if str(group.get("key") or "").strip() not in normalized_keys:
            continue
        for field in group.get("fields") or []:
            field_name = str(field.get("name") or "").strip()
            if not field_name or field_name in selected_names:
                continue
            selected_names.add(field_name)
            selected_fields.append(field)

    return selected_fields


def get_field_names(fields):
    """Return a list of non-empty name strings from a list of field dicts."""
    return [str(f.get("name") or "").strip() for f in fields if str(f.get("name") or "").strip()]
