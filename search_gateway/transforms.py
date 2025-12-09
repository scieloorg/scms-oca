from iso639 import Lang
from pycountry import countries
from django.utils.translation import gettext as _
from .data_sources_with_settings import get_display_transform_by_field_name


TRANSFORMS = {
    "language": lambda code: _(Lang(code).name),
    "country": lambda code: _(countries.get(alpha_2=code.upper()).name) if code and countries.get(alpha_2=code.upper()) else code,
}


def apply_transform(data_source, field_name, code):
    transform_type = get_display_transform_by_field_name(data_source, field_name)
    transform = TRANSFORMS.get(transform_type)
    if transform:
        try:
            return transform(code)
        except:
            return code
    return code

