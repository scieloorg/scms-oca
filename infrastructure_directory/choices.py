from django.utils.translation import gettext as _

classification = (
    ('', ''),
    ('portal', _('Portal')),
    ('plataforma', _('Plataforma')),
    ('servidor', _('Servidor')),
    ('repositório', _('Repositório')),
    ('serviço', _('Serviço')),
    ('outras', _('Outras')),
)

status = (
    ('', ''),
    ('WIP', 'WIP'),
    ('TO_MODERATE', 'TO_MODERATE'),
    ('PUBLISHED', 'PUBLISHED'),
)

