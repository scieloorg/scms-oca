import re

from django import template


register = template.Library()


LICENSE_BADGES = [
    {
        "match": ("creativecommons.org/publicdomain/zero", "cc0"),
        "label": "CC0",
        "url": "https://creativecommons.org/publicdomain/zero/1.0/",
        "slug": "cc0",
    },
    {
        "match": ("creativecommons.org/licenses/by-nc-nd", "byncnd"),
        "label": "CC-BY-NC-ND",
        "url": "https://creativecommons.org/licenses/by-nc-nd/4.0/",
        "slug": "cc-by-nc-nd",
    },
    {
        "match": ("creativecommons.org/licenses/by-nc-sa", "byncsa"),
        "label": "CC-BY-NC-SA",
        "url": "https://creativecommons.org/licenses/by-nc-sa/4.0/",
        "slug": "cc-by-nc-sa",
    },
    {
        "match": ("creativecommons.org/licenses/by-nc", "bync"),
        "label": "CC-BY-NC",
        "url": "https://creativecommons.org/licenses/by-nc/4.0/",
        "slug": "cc-by-nc",
    },
    {
        "match": ("creativecommons.org/licenses/by-nd", "bynd"),
        "label": "CC-BY-ND",
        "url": "https://creativecommons.org/licenses/by-nd/4.0/",
        "slug": "cc-by-nd",
    },
    {
        "match": ("creativecommons.org/licenses/by-sa", "bysa"),
        "label": "CC-BY-SA",
        "url": "https://creativecommons.org/licenses/by-sa/4.0/",
        "slug": "cc-by-sa",
    },
    {
        "match": ("creativecommons.org/licenses/by", "ccby"),
        "label": "CC-BY",
        "url": "https://creativecommons.org/licenses/by/4.0/",
        "slug": "cc-by",
    },
]

@register.simple_tag
def get_license_badge(rights):
    if rights is None:
        return []

    if isinstance(rights, str):
        candidates = [rights]
    elif isinstance(rights, (list, tuple, set)):
        candidates = rights
    else:
        candidates = [rights]

    badges = []
    seen = set()

    for candidate in candidates:
        text = str(candidate).strip()
        if not text:
            continue

        normalized = text.lower()
        compact = re.sub(r"[^a-z0-9]+", "", normalized)

        for badge in LICENSE_BADGES:
            if any(token in normalized or token in compact for token in badge["match"]):
                badge_key = badge["slug"]
                if badge_key in seen:
                    break

                seen.add(badge_key)
                badges.append(
                    {
                        "label": badge["label"],
                        "url": badge["url"],
                        "slug": badge["slug"],
                        "raw": text,
                    }
                )
                break

    return badges
