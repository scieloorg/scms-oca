from django.utils.translation import gettext as _


languages = (
    ('', ''),
    ('Pt', 'Pt'),
    ('Es', 'Es'),
    ('En', 'En'),
)

status = (
    ('', ''),
    ('WIP', 'WIP'),
    ('TO MODERATE', _('TO MODERATE')),
    ('PUBLISHED', _('PUBLISHED')),
)

availability = (
    ('', ''),
    ('CURRENT', _('CURRENT')),
    ('DEACTIVATED', _('DEACTIVATED')),
)

open_access = (
    ('', ''),
    ('NOT', _('NOT')),
    ('YES', _('YES')),
    ('ALL', _('ALL')),
    ('NOT APPLICABLE', _('NOT APPLICABLE')),
    ('UNDEFINED', _('UNDEFINED')),
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
