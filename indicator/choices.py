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
    ('TO_MODERATE', 'TO_MODERATE'),
    ('PUBLISHED', 'PUBLISHED'),
)

availability = (
    ('', ''),
    ('CURRENT', 'CURRENT'),
    ('DEACTIVATED', 'DEACTIVATED'),
)

open_access = (
    ('', ''),
    ('0', 'não'),
    ('1', 'sim'),
    ('2', 'ign'),
    ('3', 'all'),
)
