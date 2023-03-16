from django.utils.translation import gettext as _


languages = (
    ("", ""),
    ("Pt", "Pt"),
    ("Es", "Es"),
    ("En", "En"),
)


WIP = "WIP"
TO_MODERATE = "TO MODERATE"
PUBLISHED = "PUBLISHED"

status = (
    ("", ""),
    (WIP, _("WORK IN PROGRESS")),
    (TO_MODERATE, _("TO MODERATE")),
    (PUBLISHED, _("PUBLISHED")),
)

CURRENT = "CURRENT"
OUTDATED = "OUTDATED"

VALIDITY = (
    ("", ""),
    (CURRENT, _("CURRENT")),
    (OUTDATED, _("OUTDATED")),
)

open_access = (
    ("", ""),
    ("NOT", _("NOT")),
    ("YES", _("YES")),
    ("ALL", _("ALL")),
    ("NOT APPLICABLE", _("NOT APPLICABLE")),
    ("UNDEFINED", _("UNDEFINED")),
)


# Valores no unpaywall para `genre`
COMMUNICATION_OBJECTS = (
    ("", _("NOT APPLICABLE")),
    ("book", _("Book")),
    ("book-chapter", _("Book Chapter")),
    ("book-part", _("Part")),
    ("book-section", _("Book Section")),
    ("book-series", _("Book Series")),
    ("book-set", _("Book Set")),
    ("book-track", _("Book Track")),
    ("component", _("Component")),
    ("database", _("Database")),
    ("dataset", _("Dataset")),
    ("dissertation", _("Dissertation")),
    ("edited-book", _("Edited Book")),
    ("grant", _("Grant")),
    ("journal", _("Journal")),
    ("journal-article", _("Journal Article")),
    ("journal-issue", _("Journal Issue")),
    ("journal-volume", _("Journal Volume")),
    ("monograph", _("Monograph")),
    ("other", _("Other")),
    ("peer-review", _("Peer Review")),
    ("posted-content", _("Posted Content")),
    ("proceedings", _("Proceedings")),
    ("proceedings-article", _("Proceedings Article")),
    ("proceedings-series", _("Proceedings Series")),
    ("reference-book", _("Reference Book")),
    ("reference-entry", _("Reference Entry")),
    ("report", _("Report")),
    ("report-component", _("Report Component")),
    ("report-series", _("Report Series")),
    ("standard", _("Standard")),
)


INSTITUTIONAL = "INSTITUTIONAL"
THEMATIC = "THEMATIC"
GEOGRAPHIC = "GEOGRAPHIC"
CHRONOLOGICAL = "CHRONOLOGICAL"
GENERAL = "GENERAL"
SCOPE = (
    (GENERAL, _("Geral")),
    (INSTITUTIONAL, _("Instituticional")),
    (GEOGRAPHIC, _("Geográfico")),
    (CHRONOLOGICAL, _("Cronológico")),
    (THEMATIC, _("Temático")),
)

FREQUENCY = "FREQUENCY"
RELATIVE_FREQUENCY = "RELATIVE_FREQUENCY"
EVOLUTION = "EVOLUTION"
AVERAGE = "AVERAGE"

MEASUREMENT_TYPE = (
    ("", ""),
    (FREQUENCY, _("Frequência")),
    (EVOLUTION, _("Evolução")),
    (AVERAGE, _("Média")),
    (RELATIVE_FREQUENCY, _("Frequência relativa")),
)
