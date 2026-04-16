"""Build RIS export lines from CSL-JSON (avoids Django template access to hyphenated keys)."""

from __future__ import annotations


def _ris_escape_line(value, max_len=4000):
    if not value:
        return ""
    s = str(value).replace("\r\n", " ").replace("\n", " ").replace("\r", " ").strip()
    if len(s) > max_len:
        s = s[: max_len - 3] + "..."
    return s


def csl_items_to_ris_context(csl_json):
    rows = []
    for item in csl_json:
        year = None
        issued = item.get("issued") or {}
        dp = issued.get("date-parts")
        if isinstance(dp, list) and dp and isinstance(dp[0], list) and dp[0]:
            try:
                year = int(dp[0][0])
            except (TypeError, ValueError):
                year = dp[0][0]

        authors = item.get("author") or []
        if not isinstance(authors, list):
            authors = []

        rows.append(
            {
                "title": item.get("title"),
                "authors": authors,
                "container_title": item.get("container-title"),
                "year": year,
                "volume": item.get("volume"),
                "issue": item.get("issue"),
                "page": item.get("page"),
                "doi": item.get("DOI"),
                "url": item.get("URL"),
            }
        )
    return rows


def render_ris_lines(csl_json):
    blocks = []
    for row in csl_items_to_ris_context(csl_json):
        lines = ["TY  - JOUR"]
        if row["title"]:
            lines.append(f"TI  - {_ris_escape_line(row['title'])}")
        for author in row["authors"]:
            if not isinstance(author, dict):
                continue
            lit = author.get("literal")
            if lit:
                lines.append(f"AU  - {_ris_escape_line(lit)}")
                continue
            fam = author.get("family") or ""
            given = author.get("given") or ""
            if fam or given:
                au = f"{given} {fam}".strip()
                lines.append(f"AU  - {_ris_escape_line(au)}")
        if row["container_title"]:
            lines.append(f"JO  - {_ris_escape_line(row['container_title'])}")
        if row["year"] is not None:
            lines.append(f"PY  - {row['year']}")
        if row["volume"]:
            lines.append(f"VL  - {_ris_escape_line(row['volume'])}")
        if row["issue"]:
            lines.append(f"IS  - {_ris_escape_line(row['issue'])}")
        if row["page"]:
            lines.append(f"SP  - {_ris_escape_line(row['page'])}")
        if row["doi"]:
            lines.append(f"DO  - {_ris_escape_line(row['doi'])}")
        if row["url"]:
            lines.append(f"UR  - {_ris_escape_line(row['url'])}")
        lines.append("ER  -")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks) + ("\n" if blocks else "")
