import csv
import io

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from enrichment.constants import WORLD_REGIONS_REQUIRED_COLUMNS


def _create_csv_reader(csv_file):
    csv_content = csv_file.read()

    if isinstance(csv_content, bytes):
        try:
            csv_content = csv_content.decode("utf-8-sig")
        except UnicodeDecodeError as error:
            raise ValidationError(_("O arquivo deve estar em UTF-8.")) from error

    try:
        dialect = csv.Sniffer().sniff(csv_content[:4096], delimiters=";,")
    except csv.Error as error:
        raise ValidationError(
            _("Não foi possível identificar o delimitador do arquivo.")
        ) from error

    reader = csv.DictReader(io.StringIO(csv_content), dialect=dialect)

    return reader


def _parse_world_region_row(row, row_number):
    country_code = (row.get("country_code") or "").strip().upper()
    world_region = (row.get("world_region") or "").strip()

    if (
        len(country_code) != 2
        or not country_code.isascii()
        or not country_code.isalpha()
    ):
        raise ValidationError(
            _("Código de país inválido na linha %(line)s.") % {"line": row_number}
        )

    if not world_region:
        raise ValidationError(
            _("Região ausente na linha %(line)s.") % {"line": row_number}
        )

    return country_code, world_region


def parse_world_regions_csv(csv_file):
    reader = _create_csv_reader(csv_file)

    missing_columns = WORLD_REGIONS_REQUIRED_COLUMNS - set(reader.fieldnames or [])
    if missing_columns:
        columns = ", ".join(sorted(missing_columns))
        raise ValidationError(
            _("O arquivo deve conter as colunas obrigatórias: %(columns)s.")
            % {"columns": columns}
        )

    regions_by_country_code = {}
    for row_number, row in enumerate(reader, start=2):
        country_code, world_region = _parse_world_region_row(row, row_number)

        if country_code in regions_by_country_code:
            raise ValidationError(
                _("Código de país duplicado na linha %(line)s.") % {"line": row_number}
            )

        regions_by_country_code[country_code] = world_region

    if not regions_by_country_code:
        raise ValidationError(_("O arquivo não contém regiões."))

    return regions_by_country_code
