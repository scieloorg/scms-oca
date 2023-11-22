import logging

from django.contrib.auth import get_user_model
from django.utils.translation import gettext as _

from indicator.tasks import task_generate_article_indicators

logger = logging.getLogger(__name__)

User = get_user_model()

def run(user_id=1):
    """
    This will loop up to all itens on index and generate the graph.
    """
    user = User.objects.get(id=user_id)

    indicators = [
        {
            "filters": [],
            "title": "Evolução do número de artigos científicos com e sem APC por instituição 2012-2023 - Brasil",
            "facet_by": "year",
            "description": "Gerado automaticamente usando dados coletados do OpenALex no perído de 2012 até 2023",
            "context_by": ["institutions", "apc"],
            "default_filter": {"record_type": "article"},
            "range_filter": {
                "filter_name": "year",
                "range": {"start": 2012, "end": 2023}
            }
        },
        {
            "filters": [],
            "title": "Evolução do número de artigos científicos com e sem APC por UF 2012-2023 - Brasil",
            "facet_by": "year",
            "description": "Gerado automaticamente usando dados coletados do OpenALex no perído de 2012 até 2023",
            "context_by": ["states", "apc"],
            "default_filter": {"record_type": "article"},
            "range_filter": {
                "filter_name": "year",
                "range": {"start": 2012, "end": 2023}
            }
        },
        {
            "filters": [],
            "title": "Evolução do número de artigos científicos com e sem APC por área temática 2012-2023 - Brasil",
            "facet_by": "year",
            "description": "Gerado automaticamente usando dados coletados do OpenALex no perído de 2012 até 2023",
            "context_by": ["thematic_level_0", "apc"],
            "default_filter": {"record_type": "article"},
            "range_filter": {
                "filter_name": "year",
                "range": {"start": 2012, "end": 2023}
            }
        },
        {
            "filters": [],
            "title": "Evolução do número de artigos científicos por licença e instituição 2012-2023 - Brasil",
            "facet_by": "year",
            "description": "Gerado automaticamente usando dados coletados do OpenALex no perído de 2012 até 2023",
            "context_by": ["institutions", "license"],
            "default_filter": {"record_type": "article"},
            "range_filter": {
                "filter_name": "year",
                "range": {"start": 2012, "end": 2023}
            }
        },
        {
            "filters": [],
            "title": "Evolução do número de artigos científicos por licença e UF 2012-2023 - Brasil",
            "facet_by": "year",
            "description": "Gerado automaticamente usando dados coletados do OpenALex no perído de 2012 até 2023",
            "context_by": ["states", "license"],
            "default_filter": {"record_type": "article"},
            "range_filter": {
                "filter_name": "year",
                "range": {"start": 2012, "end": 2023}
            }
        },
        {
            "filters": [],
            "title": "Evolução do número de artigos científicos por licença e área temática 2012-2023 - Brasil",
            "facet_by": "year",
            "description": "Gerado automaticamente usando dados coletados do OpenALex no perído de 2012 até 2023",
            "context_by": ["thematic_level_0", "license"],
            "default_filter": {"record_type": "article"},
            "range_filter": {
                "filter_name": "year",
                "range": {"start": 2012, "end": 2023}
            }
        },
        {
            "filters": [],
            "title": "Evolução do número de artigos científicos por tipo de acesso aberto e instituiç 2012-2023 - Brasil",
            "facet_by": "year",
            "description": "Gerado automaticamente usando dados coletados do OpenALex no perído de 2012 até 2023",
            "context_by": ["institutions", "open_access_status"],
            "default_filter": {"record_type": "article"},
            "range_filter": {
                "filter_name": "year",
                "range": {"start": 2012, "end": 2023}
            }
        },
        {
            "filters": [],
            "title": "Evolução do número de artigos científicos por tipo de acesso aberto e UF 2012-2023 - Brasil",
            "facet_by": "year",
            "description": "Gerado automaticamente usando dados coletados do OpenALex no perído de 2012 até 2023",
            "context_by": ["open_access_status", "states"],
            "default_filter": {"record_type": "article"},
            "range_filter": {
                "filter_name": "year",
                "range": {"start": 2012, "end": 2023}
            }
        },
        {
            "filters": [],
            "title": "Evolução do número de artigos científicos por tipo de acesso aberto e área temática 2012-2023 - Brasil",
            "facet_by": "year",
            "description": "Gerado automaticamente usando dados coletados do OpenALex no perído de 2012 até 2023",
            "context_by": ["thematic_level_0", "open_access_status"],
            "default_filter": {"record_type": "article"},
            "range_filter": {
                "filter_name": "year",
                "range": {"start": 2012, "end": 2023}
            }
        },
        {
            "filters": [],
            "title": "Número de ações em ciência aberta por área temática e regiões",
            "facet_by": "action",
            "description": "Gerado automaticamente usando dados coletados e registrados manualmente por SciELO",
            "context_by": ["thematic_areas", "regions"],
            "default_filter": {"record_type": "directory"},
            "range_filter": None,
            "fill_range": True, 
        },
        {
            "filters": [],
            "title": "Número de ações em ciência aberta por área temática e UF",
            "facet_by": "action",
            "description": "Gerado automaticamente usando dados coletados e registrados manualmente por SciELO",
            "context_by": ["thematic_areas", "states"],
            "default_filter": {"record_type": "directory"},
            "range_filter": None,
            "fill_range": True, 
        },
        {
            "filters": [],
            "title": "Número de ações em ciência aberta por área temática e instituições",
            "facet_by": "action",
            "description": "Gerado automaticamente usando dados coletados e registrados manualmente por SciELO",
            "context_by": ["institutions", "thematic_areas"],
            "default_filter": {"record_type": "directory"},
            "range_filter": None,
            "fill_range": True, 
        },
        {
            "filters": [],
            "title": "Número de ações em ciência aberta por área região e instituições",
            "facet_by": "action",
            "description": "Gerado automaticamente usando dados coletados e registrados manualmente por SciELO",
            "context_by": ["regions", "institutions"],
            "default_filter": {"record_type": "directory"},
            "range_filter": None,
            "fill_range": True, 
        },
        {
            "filters": [],
            "title": "Número de ações em ciência aberta área temática",
            "facet_by": "action",
            "description": "Gerado automaticamente usando dados coletados e registrados manualmente por SciELO",
            "context_by": ["thematic_areas"],
            "default_filter": {"record_type": "directory"},
            "range_filter": None,
            "fill_range": True, 
        },
        {
            "filters": [],
            "title": "Número de ações em ciência aberta por regiões",
            "facet_by": "action",
            "description": "Gerado automaticamente usando dados coletados e registrados manualmente por SciELO",
            "context_by": ["regions"],
            "default_filter": {"record_type": "directory"},
            "range_filter": None,
            "fill_range": True, 
        },
        {
            "filters": [],
            "title": "Número de ações em ciência aberta por instituição e UF",
            "facet_by": "action",
            "description": "Gerado automaticamente usando dados coletados e registrados manualmente por SciELO",
            "context_by": ["institutions", "states"],
            "default_filter": {"record_type": "directory"},
            "range_filter": None,
            "fill_range": True, 
        },
    ]

    task_generate_article_indicators.apply_async(args=(int(user_id), indicators))