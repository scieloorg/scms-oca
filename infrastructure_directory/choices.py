from django.utils.translation import gettext as _

classification = (
    ("", ""),
    ("portal", _("Portal")),
    ("plataforma", _("Plataforma")),
    ("servidor", _("Servidor")),
    ("repositório", _("Repositório")),
    ("repositório_de_dados", _("Repositório de dados")),
    ("repositório_de_dados_de_pesquisa", _("Repositório de dados de pesquisa")),
    ("portal_de_periódicos", _("Portal de periódicos")),
    ("websites","Websites"),
    ("serviço", _("Serviço")),
    ("outras", _("Outras")),
)

status = (
    ("", ""),
    ("WIP", "WIP"),
    ("TO MODERATE", _("TO MODERATE")),
    ("PUBLISHED", _("PUBLISHED")),
    ("NOT PUBLISHED", _("NOT PUBLISHED")),
)

