from django.utils.translation import gettext as _

classification = (
    ('', ''),
    ('curso livre', _('curso livre')),
    ('disciplina de graduação', _('disciplina de graduação')),
    ('disciplina de lato sensu', _('disciplina de lato sensu')),
    ('disciplina de stricto sensu', _('disciplina de stricto sensu')),
    ('outros', _('outros')),
)

status = (
    ('', ''),
    ('WIP', 'WIP'),
    ('TO_MODERATE', 'TO_MODERATE'),
    ('PUBLISHED', 'PUBLISHED'),
)
