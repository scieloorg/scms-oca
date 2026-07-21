import csv
import io

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def parse_world_regions(file_obj):
    file_obj.seek(0)
    content = file_obj.read()
    file_obj.seek(0)

    if isinstance(content, bytes):
        try:
            content = content.decode("utf-8-sig")
        except UnicodeDecodeError as error:
            raise ValidationError(_("O arquivo deve estar em UTF-8.")) from error

    try:
        dialect = csv.Sniffer().sniff(content[:4096], delimiters=";,")
    except csv.Error as error:
        raise ValidationError(
            _("Não foi possível identificar o delimitador do CSV.")
        ) from error

    reader = csv.DictReader(io.StringIO(content), dialect=dialect)
    required_columns = {"country_code", "world_region"}
    if not required_columns.issubset(reader.fieldnames or []):
        raise ValidationError(
            _("O CSV deve conter as colunas country_code e world_region.")
        )

    mapping = {}
    for row_number, row in enumerate(reader, start=2):
        country_code = (row.get("country_code") or "").strip().upper()
        world_region = (row.get("world_region") or "").strip()
        
        if len(country_code) != 2 or not country_code.isalpha():
            raise ValidationError(
                _("Código de país inválido na linha %(line)s.") % {"line": row_number}
            )
        
        if not world_region:
            raise ValidationError(
                _("Região ausente na linha %(line)s.") % {"line": row_number}
            )
        
        if country_code in mapping:
            raise ValidationError(
                _("Código de país duplicado na linha %(line)s.") % {"line": row_number}
            )

        mapping[country_code] = world_region

    if not mapping:
        raise ValidationError(_("O CSV não contém regiões."))

    return dict(sorted(mapping.items()))
