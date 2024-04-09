import logging

from django.contrib.auth import get_user_model
from django.utils.translation import gettext as _

from indicator.tasks import task_generate_indicators_by_oa_api

logger = logging.getLogger(__name__)

User = get_user_model()


def run(user_id=1):
    """
    This will loop up to all itens on index and generate the graph.
    """
    user = User.objects.get(id=user_id)

    indicators = [
        # Por tipo de documento (Mundo)
        {
            "title": "Quantidade de documentos por tipo entre os anos de 2014 até 2023",
            "description": "Gerado a partir da coleta da somatória dos registro do OpenALex no período de 2014 até 2023",
            "group_by": "type",
            "filters": {},
            "range_year": {"start": 2014, "end": 2023},
            "stacked": True,
        },
        {
            "title": "Quantidade de documentos por tipo em acesso aberto entre os anos de 2014 até 2023",
            "description": "Gerado a partir da coleta da somatória dos registro do OpenALex no período de 2014 até 2023",
            "group_by": "type",
            "filters": {"is_oa": True},
            "range_year": {"start": 2014, "end": 2023},
            "stacked": True,
        },
        {
            "title": "Quantidade de documentos por tipo em acesso aberto Gold entre os anos de 2014 até 2023",
            "description": "Gerado a partir da coleta da somatória dos registro do OpenALex no período de 2014 até 2023",
            "group_by": "type",
            "filters": {"is_oa": True, "open_access.oa_status": "gold"},
            "range_year": {"start": 2014, "end": 2023},
            "stacked": True,
        },

        # Quantidade de artigos (Brasil)
        {
            "title": "Quantidade de artigos no Brasil entre 2014 e 2023",
            "description": "Gerado a partir da coleta da somatória dos registro do OpenALex no período de 2014 até 2023",
            "group_by": "publication_year",
            "filters": {"institutions.country_code": "br", "type": "article"},
            "range_year": {"start": 2014, "end": 2023},
            "stacked": False,
        },
        {
            "title": "Quantidade de artigos no Brasil em acesso aberto entre 2014 até 2023",
            "description": "Gerado a partir da coleta da somatória dos registro do OpenALex no período de 2014 até 2023",
            "group_by": "publication_year",
            "filters": {"is_oa": True, "institutions.country_code": "br", "type": "article"},
            "range_year": {"start": 2014, "end": 2023},
            "stacked": False,
        },
        {
            "title": "Quantidade de artigos no Brasil em acesso aberto Gold Brasil entre 2014 até 2023",
            "description": "Gerado a partir da coleta da somatória dos registro do OpenALex no período de 2014 até 2023",
            "group_by": "publication_year",
            "filters": {"is_oa": True, "institutions.country_code": "br", "open_access.oa_status": "gold", "type": "article"},
            "range_year": {"start": 2014, "end": 2023},
            "stacked": False,
        },

        # Por tipo de documentos no Brasil
        {
            "title": "Quantidade de documentos por tipo no Brasil entre os anos de 2014 até 2023",
            "description": "Gerado a partir da coleta da somatória dos registro do OpenALex no período de 2014 até 2023.",
            "group_by": "type",
            "filters": {"institutions.country_code": "br"},
            "range_year": {"start": 2014, "end": 2023},
            "stacked": True,
        },
        {
            "title": "Quantidade de documentos por tipo em acesso aberto no Brasil entre os anos de 2014 até 2023",
            "description": "Gerado a partir da coleta da somatória dos registro do OpenALex no período de 2014 até 2023.",
            "group_by": "type",
            "filters": {"is_oa": True, "institutions.country_code": "br"},
            "range_year": {"start": 2014, "end": 2023},
            "stacked": True,
        },
        {
            "title": "Quantidade de documentos por tipo em acesso aberto Gold no Brasil entre os anos de 2014 até 2023",
            "description": "Gerado a partir da coleta da somatória dos registro do OpenALex no período de 2014 até 2023.",
            "group_by": "type",
            "filters": {"is_oa": True, "institutions.country_code": "br", "open_access.oa_status": "gold"},
            "range_year": {"start": 2014, "end": 2023},
            "stacked": True,
        }
    ]
    
    task_generate_indicators_by_oa_api(int(user_id), indicators)
