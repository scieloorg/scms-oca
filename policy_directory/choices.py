from django.utils.translation import gettext as _

classification = (
    ("", ""),
    ("promoção", _("promoção")),
    ("posicionamento", _("posicionamento")),
    ("mandato", _("mandato")),
    ("geral", _("geral")),
)

status = (
    ("", ""),
    ("WIP", "WIP"),
    ("TO MODERATE", _("TO MODERATE")),
    ("PUBLISHED", _("PUBLISHED")),
    ("NOT PUBLISHED", _("NOT PUBLISHED")),
)
