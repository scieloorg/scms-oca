from collections import OrderedDict


def build_form_groups(fields, form_group_labels=None):
    fields = [field for field in (fields or []) if field.get("has_visible_content")]
    form_group_labels = form_group_labels or {}
    grouped_fields = OrderedDict()
    for field in fields:
        group_key = field["group"]["key"]
        group_label = form_group_labels.get(group_key, field["group"]["label"])
        if group_key not in grouped_fields:
            grouped_fields[group_key] = {
                "key": group_key,
                "label": group_label,
                "order": field["group"]["order"],
                "fields": [],
            }
        grouped_fields[group_key]["fields"].append(field)

    grouped_items = sorted(grouped_fields.values(), key=lambda item: (item["order"], item["label"]))
    has_active_fields = any(
        field.get("is_active")
        for group in grouped_items
        for field in group.get("fields", [])
    )

    for group in grouped_items:
        group_is_active = any(field.get("is_active") for field in group.get("fields", []))
        group["expanded"] = group_is_active if has_active_fields else True
        for field in group.get("fields", []):
            field["expanded"] = field.get("is_active") if has_active_fields else True

    return grouped_items
