from django.utils.translation import gettext as _


attendence_type = (
    ('', ''),
    ('live', 'Live'),  # All attendees are physically present in one location
    ('virtual', 'Virtual'),  # People attend the event entirely online
    ('hybrid', 'Hybrid'),  # Some people attend in person, others online
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

status = (
    ('', ''),
    ('WIP', 'WIP'),
    ('TO_MODERATE', 'TO_MODERATE'),
    ('PUBLISHED', 'PUBLISHED'),
)
