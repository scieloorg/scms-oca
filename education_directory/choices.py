from django.utils.translation import gettext as _

classification = (
    ('', ''),
    ('curso livre', _('curso livre')),
    ('disciplina de graduação', _('disciplina de graduação')),
    ('disciplina de lato sensu', _('disciplina de lato sensu')),
    ('disciplina de stricto sensu', _('disciplina de stricto sensu')),
    ('outros', _('outros')),
)

attendance_type = (
    ('', ''),
    ('live', 'Presencial'),  # All attendees are physically present in one location
    ('virtual', 'Remoto'),  # People attend the event entirely online
    ('hybrid', 'Híbrido'),  # Some people attend in person, others online
)
