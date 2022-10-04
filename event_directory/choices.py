from django.utils.translation import gettext as _


attendance_type = (
    ('', ''),
    ('live', 'Presencial'),  # All attendees are physically present in one location
    ('virtual', 'Remoto'),  # People attend the event entirely online
    ('hybrid', 'Híbrido'),  # Some people attend in person, others online
)

classification = (
    ('', ''),
    ('encontro', _('encontro')),
    ('conferência', _('conferência')),
    ('congresso', _('congresso')),
    ('workshop', _('workshop')),
    ('seminário', _('seminário')),
    ('outros', _('outros')),
)
