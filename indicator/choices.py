from django.utils.translation import gettext as _


languages = (
    ('', ''),
    ('Pt', 'Pt'),
    ('Es', 'Es'),
    ('En', 'En'),
)


WIP = 'WIP'
TO_MODERATE = 'TO MODERATE'
PUBLISHED = 'PUBLISHED'

status = (
    ('', ''),
    (WIP, _('WORK IN PROGRESS')),
    (TO_MODERATE, _('TO MODERATE')),
    (PUBLISHED, _('PUBLISHED')),
)

CURRENT = 'CURRENT'
OUTDATED = 'OUTDATED'

VALIDITY = (
    ('', ''),
    (CURRENT, _('CURRENT')),
    (OUTDATED, _('OUTDATED')),
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


INSTITUTIONAL = 'INSTITUTIONAL'
THEMATIC = 'THEMATIC'
GEOGRAPHIC = 'GEOGRAPHIC'
CHRONOLOGICAL = 'CHRONOLOGICAL'

SCOPE = (
    ('', ''),
    (INSTITUTIONAL, _('Instituticional')),
    (GEOGRAPHIC, _('Geográfico')),
    (CHRONOLOGICAL, _('Cronológico')),
    (THEMATIC, _('Temático')),
)
