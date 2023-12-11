import json
import django
import zoneinfo
from django_celery_beat.models import CrontabSchedule, PeriodicTask


# This script create all tasks necessary to the project.
# The list os task create are:
# Load OpenAlex data to SourceArticle
# Load ArticleSource to Article
# Load OpenAlex Institution data to SourceInstitution
# Load OpenAlex Concepts
# Update the Institution entity with the matching SourceInstitution
# Match between contributor institutions and set corresponding affiliations
# Realiza o casamento entre o modelo de afiliação(Affiliation) atributo source com sua correspondência no modelo de instituição quando a instituição Match between affiliation.source and Institution[MEC]
# Generate scientific indicator


def run(recreate=True):
    if recreate:
        PeriodicTask.objects.all().delete()
        CrontabSchedule.objects.all().delete()

    tasks = {
        "tasks": [
            {
                "name": "Load OpenAlex data to SourceArticle",
                "task": "article.tasks.load_openalex",
                "args": json.dumps([]),
                "kwargs": json.dumps({"date": 2012, "length": None, "country": "BR"}),
                "enabled": False,
                "description": "Esse processamento carrega os dados da produção científica do Brasil para o OCABR. Consulta a API do OpenALex: https://api.openalex.org/",
            },
            {
                "name": "Load OpenAlex Institution data to SourceInstitution",
                "task": "institution.tasks.load_institution",
                "args": json.dumps([]),
                "kwargs": json.dumps({"length": None, "country": "BR"}),
                "enabled": False,
                "description": "Essa tarefa cadastrar as instituições do OpenAlex no modelo de Source Institution Consulta a API do OpenALex: https://api.openalex.org/institutions",
            },
            {
                "name": "Load OpenAlex Concepts",
                "task": "article.tasks.load_openalex_concepts",
                "args": json.dumps([]),
                "kwargs": json.dumps({"delete": False}),
                "enabled": False,
                "description": "Carrega todos os conceitos do OpenAlex da API: https://api.openalex.org/concepts. Os concepts são um total de 65026",
            },
            {
                "name": "Update the Institution entity with the matching SourceInstitution",
                "task": "institution.tasks.update_inst_by_source_inst",
                "args": json.dumps([]),
                "kwargs": json.dumps({"source": "MEC"}),
                "enabled": False,
                "description": "Esta tarefa atualiza o modelo de Instituição com seu respectivo vínculo com SourceInstitution.",
            },
            {
                "name": "Match between contributor institutions and set corresponding affiliations",
                "task": "article.tasks.match_contrib_inst_aff",
                "args": json.dumps([]),
                "kwargs": json.dumps({}),
                "enabled": False,
                "description": "Esta tarefa se estende a todos os contribuidores que procuram contribuintes.instituições e encontram a afiliação Atualiza o affiliation.source do contribuidor",
            },
            {
                "name": "Match between affiliation.source and Institution[MEC]",
                "task": "article.tasks.match_contrib_aff_source_with_inst_MEC",
                "args": json.dumps([]),
                "kwargs": json.dumps({}),
                "enabled": False,
                "description": "Esta tarefa percorre todas as afiliações em busca de affiliation.source e encontra a instituição do MEC",
            },
            {
                "name": "Load ArticleSource to Article",
                "task": "article.tasks.article_source_to_article",
                "args": json.dumps([]),
                "kwargs": json.dumps(
                    {
                        "size": None,
                        "loop_size": 1000,
                        "institution_id": None,
                        "year": 2012,
                    }
                ),
                "enabled": False,
                "description": "Essa tarefa obtém os dados de SourceArticle para Article.",
            },
            {
                "name": "Generate scientific indicator",
                "task": "Generate scientific indicator",
                "args": json.dumps([]),
                "kwargs": json.dumps(
                    {
                        "indicators": [
                            {
                                "filters": [],
                                "title": "Evolução do número de artigos científicos com e sem APC por instituição 2012-2022 - Brasil",
                                "facet_by": "year",
                                "description": "Gerado automaticamente usando dados coletados do OpenALex no perído de 2012 até 2022",
                                "context_by": ["institutions", "apc"],
                                "default_filter": {"record_type": "article"},
                                "range_filter": {
                                    "filter_name": "year",
                                    "range": {"start": 2012, "end": 2022}
                                },
                                "models": ["article"],
                            },
                            {
                                "filters": [],
                                "title": "Evolução do número de artigos científicos em acesso aberto com e sem APC por instituição 2012-2022 - Brasil",
                                "facet_by": "year",
                                "description": "Gerado automaticamente usando dados coletados do OpenALex no perído de 2012 até 2022",
                                "context_by": ["institutions", "apc"],
                                "default_filter": {"record_type": "article", "is_oa":"true"},
                                "range_filter": {
                                    "filter_name": "year",
                                    "range": {"start": 2012, "end": 2022}
                                },
                                "models": ["article"],
                            },
                            {
                                "filters": [],
                                "title": "Evolução do número de artigos científicos sem acesso aberto com e sem APC por instituição 2012-2022 - Brasil",
                                "facet_by": "year",
                                "description": "Gerado automaticamente usando dados coletados do OpenALex no perído de 2012 até 2022",
                                "context_by": ["institutions", "apc"],
                                "default_filter": {"record_type": "article", "is_oa":"false"},
                                "range_filter": {
                                    "filter_name": "year",
                                    "range": {"start": 2012, "end": 2022}
                                },
                                "models": ["article"],
                            },
                            {
                                "filters": [],
                                "title": "Evolução do número de artigos científicos com e sem APC por UF 2012-2022 - Brasil",
                                "facet_by": "year",
                                "description": "Gerado automaticamente usando dados coletados do OpenALex no perído de 2012 até 2022",
                                "context_by": ["states", "apc"],
                                "default_filter": {"record_type": "article"},
                                "range_filter": {
                                    "filter_name": "year",
                                    "range": {"start": 2012, "end": 2022},
                                },
                                "models": ["article"],
                            },
                            {
                                "filters": [],
                                "title": "Evolução do número de artigos científicos em acesso aberto com e sem APC por UF 2012-2022 - Brasil",
                                "facet_by": "year",
                                "description": "Gerado automaticamente usando dados coletados do OpenALex no perído de 2012 até 2022",
                                "context_by": ["states", "apc"],
                                "default_filter": {"record_type": "article", "is_oa":"true"},
                                "range_filter": {
                                    "filter_name": "year",
                                    "range": {"start": 2012, "end": 2022},
                                },
                                "models": ["article"],
                            },
                            {
                                "filters": [],
                                "title": "Evolução do número de artigos científicos sem acesso aberto com e sem APC por UF 2012-2022 - Brasil",
                                "facet_by": "year",
                                "description": "Gerado automaticamente usando dados coletados do OpenALex no perído de 2012 até 2022",
                                "context_by": ["states", "apc"],
                                "default_filter": {"record_type": "article", "is_oa":"false"},
                                "range_filter": {
                                    "filter_name": "year",
                                    "range": {"start": 2012, "end": 2022},
                                },
                                "models": ["article"],
                            },
                            {
                                "filters": [],
                                "title": "Evolução do número de artigos científicos com e sem APC por área temática 2012-2022 - Brasil",
                                "facet_by": "year",
                                "description": "Gerado automaticamente usando dados coletados do OpenALex no perído de 2012 até 2022",
                                "context_by": ["thematic_level_0", "apc"],
                                "default_filter": {"record_type": "article"},
                                "range_filter": {
                                    "filter_name": "year",
                                    "range": {"start": 2012, "end": 2022},
                                },
                                "models": ["article"] 
                            },
                            {
                                "filters": [],
                                "title": "Evolução do número de artigos científicos em acesso aberto com e sem APC por área temática 2012-2022 - Brasil",
                                "facet_by": "year",
                                "description": "Gerado automaticamente usando dados coletados do OpenALex no perído de 2012 até 2022",
                                "context_by": ["thematic_level_0", "apc"],
                                "default_filter": {"record_type": "article", "is_oa":"true"},
                                "range_filter": {
                                    "filter_name": "year",
                                    "range": {"start": 2012, "end": 2022},
                                },
                                "models": ["article"] 
                            },
                            {
                                "filters": [],
                                "title": "Evolução do número de artigos científicos sem acesso aberto com e sem APC por área temática 2012-2022 - Brasil",
                                "facet_by": "year",
                                "description": "Gerado automaticamente usando dados coletados do OpenALex no perído de 2012 até 2022",
                                "context_by": ["thematic_level_0", "apc"],
                                "default_filter": {"record_type": "article", "is_oa":"false"},
                                "range_filter": {
                                    "filter_name": "year",
                                    "range": {"start": 2012, "end": 2022},
                                },
                                "models": ["article"] 
                            },
                            {
                                "filters": [],
                                "title": "Evolução do número de artigos científicos por licença e instituição 2012-2022 - Brasil",
                                "facet_by": "year",
                                "description": "Gerado automaticamente usando dados coletados do OpenALex no perído de 2012 até 2022",
                                "context_by": ["institutions", "license"],
                                "default_filter": {"record_type": "article"},
                                "range_filter": {
                                    "filter_name": "year",
                                    "range": {"start": 2012, "end": 2022}
                                },
                                "models": ["article"], 
                            },
                            {
                                "filters": [],
                                "title": "Evolução do número de artigos científicos em acesso aberto por licença e instituição 2012-2022 - Brasil",
                                "facet_by": "year",
                                "description": "Gerado automaticamente usando dados coletados do OpenALex no perído de 2012 até 2022",
                                "context_by": ["institutions", "license"],
                                "default_filter": {"record_type": "article", "is_oa":"true"},
                                "range_filter": {
                                    "filter_name": "year",
                                    "range": {"start": 2012, "end": 2022}
                                },
                                "models": ["article"], 
                            },
                            {
                                "filters": [],
                                "title": "Evolução do número de artigos científicos sem acesso aberto por licença e instituição 2012-2022 - Brasil",
                                "facet_by": "year",
                                "description": "Gerado automaticamente usando dados coletados do OpenALex no perído de 2012 até 2022",
                                "context_by": ["institutions", "license"],
                                "default_filter": {"record_type": "article", "is_oa":"false"},
                                "range_filter": {
                                    "filter_name": "year",
                                    "range": {"start": 2012, "end": 2022}
                                },
                                "models": ["article"], 
                            },
                            {
                                "filters": [],
                                "title": "Evolução do número de artigos científicos por licença e UF 2012-2022 - Brasil",
                                "facet_by": "year",
                                "description": "Gerado automaticamente usando dados coletados do OpenALex no perído de 2012 até 2022",
                                "context_by": ["states", "license"],
                                "default_filter": {"record_type": "article"},
                                "range_filter": {
                                    "filter_name": "year",
                                    "range": {"start": 2012, "end": 2022}
                                },
                                "models": ["article"], 
                            },
                            {
                                "filters": [],
                                "title": "Evolução do número de artigos científicos em acesso aberto por licença e UF 2012-2022 - Brasil",
                                "facet_by": "year",
                                "description": "Gerado automaticamente usando dados coletados do OpenALex no perído de 2012 até 2022",
                                "context_by": ["states", "license"],
                                "default_filter": {"record_type": "article", "is_oa":"true"},
                                "range_filter": {
                                    "filter_name": "year",
                                    "range": {"start": 2012, "end": 2022}
                                },
                                "models": ["article"], 
                            },
                            {
                                "filters": [],
                                "title": "Evolução do número de artigos científicos sem acesso aberto por licença e UF 2012-2022 - Brasil",
                                "facet_by": "year",
                                "description": "Gerado automaticamente usando dados coletados do OpenALex no perído de 2012 até 2022",
                                "context_by": ["states", "license"],
                                "default_filter": {"record_type": "article", "is_oa":"false"},
                                "range_filter": {
                                    "filter_name": "year",
                                    "range": {"start": 2012, "end": 2022}
                                },
                                "models": ["article"], 
                            },
                            {
                                "filters": [],
                                "title": "Evolução do número de artigos científicos por licença e área temática 2012-2022 - Brasil",
                                "facet_by": "year",
                                "description": "Gerado automaticamente usando dados coletados do OpenALex no perído de 2012 até 2022",
                                "context_by": ["thematic_level_0", "license"],
                                "default_filter": {"record_type": "article"},
                                "range_filter": {
                                    "filter_name": "year",
                                    "range": {"start": 2012, "end": 2022}
                                },
                                "models": ["article"], 
                            },
                            {
                                "filters": [],
                                "title": "Evolução do número de artigos científicos em acesso aberto por licença e área temática 2012-2022 - Brasil",
                                "facet_by": "year",
                                "description": "Gerado automaticamente usando dados coletados do OpenALex no perído de 2012 até 2022",
                                "context_by": ["thematic_level_0", "license"],
                                "default_filter": {"record_type": "article", "is_oa":"true"},
                                "range_filter": {
                                    "filter_name": "year",
                                    "range": {"start": 2012, "end": 2022}
                                },
                                "models": ["article"], 
                            },
                            {
                                "filters": [],
                                "title": "Evolução do número de artigos científicos sem acesso aberto por licença e área temática 2012-2022 - Brasil",
                                "facet_by": "year",
                                "description": "Gerado automaticamente usando dados coletados do OpenALex no perído de 2012 até 2022",
                                "context_by": ["thematic_level_0", "license"],
                                "default_filter": {"record_type": "article", "is_oa":"false"},
                                "range_filter": {
                                    "filter_name": "year",
                                    "range": {"start": 2012, "end": 2022}
                                },
                                "models": ["article"], 
                            },
                            {
                                "filters": [],
                                "title": "Evolução do número de artigos científicos por tipo de acesso aberto e instituição 2012-2022 - Brasil",
                                "facet_by": "year",
                                "description": "Gerado automaticamente usando dados coletados do OpenALex no perído de 2012 até 2022",
                                "context_by": ["institutions", "open_access_status"],
                                "default_filter": {"record_type": "article"},
                                "range_filter": {
                                    "filter_name": "year",
                                    "range": {"start": 2012, "end": 2022}
                                }
                            },
                            {
                                "filters": [],
                                "title": "Evolução do número de artigos científicos em acesso aberto por tipo de acesso aberto e instituição 2012-2022 - Brasil",
                                "facet_by": "year",
                                "description": "Gerado automaticamente usando dados coletados do OpenALex no perído de 2012 até 2022",
                                "context_by": ["institutions", "open_access_status"],
                                "default_filter": {"record_type": "article", "is_oa":"true"},
                                "range_filter": {
                                    "filter_name": "year",
                                    "range": {"start": 2012, "end": 2022}
                                }
                            },
                            {
                                "filters": [],
                                "title": "Evolução do número de artigos científicos sem acesso aberto por tipo de acesso aberto e instituição 2012-2022 - Brasil",
                                "facet_by": "year",
                                "description": "Gerado automaticamente usando dados coletados do OpenALex no perído de 2012 até 2022",
                                "context_by": ["institutions", "open_access_status"],
                                "default_filter": {"record_type": "article", "is_oa":"false"},
                                "range_filter": {
                                    "filter_name": "year",
                                    "range": {"start": 2012, "end": 2022}
                                }
                            },
                            {
                                "filters": [],
                                "title": "Evolução do número de artigos científicos por tipo de acesso aberto e UF 2012-2022 - Brasil",
                                "facet_by": "year",
                                "description": "Gerado automaticamente usando dados coletados do OpenALex no perído de 2012 até 2022",
                                "context_by": ["open_access_status", "states"],
                                "default_filter": {"record_type": "article"},
                                "range_filter": {
                                    "filter_name": "year",
                                    "range": {"start": 2012, "end": 2022}
                                }
                            },
                            {
                                "filters": [],
                                "title": "Evolução do número de artigos científicos com acesso aberto por tipo de acesso aberto e UF 2012-2022 - Brasil",
                                "facet_by": "year",
                                "description": "Gerado automaticamente usando dados coletados do OpenALex no perído de 2012 até 2022",
                                "context_by": ["open_access_status", "states"],
                                "default_filter": {"record_type": "article", "is_oa":"true"},
                                "range_filter": {
                                    "filter_name": "year",
                                    "range": {"start": 2012, "end": 2022}
                                }
                            },
                            {
                                "filters": [],
                                "title": "Evolução do número de artigos científicos sem acesso aberto  por tipo de acesso aberto e UF 2012-2022 - Brasil",
                                "facet_by": "year",
                                "description": "Gerado automaticamente usando dados coletados do OpenALex no perído de 2012 até 2022",
                                "context_by": ["open_access_status", "states"],
                                "default_filter": {"record_type": "article", "is_oa":"false"},
                                "range_filter": {
                                    "filter_name": "year",
                                    "range": {"start": 2012, "end": 2022}
                                }
                            },
                            {
                                "filters": [],
                                "title": "Evolução do número de artigos científicos por tipo de acesso aberto e área temática 2012-2022 - Brasil",
                                "facet_by": "year",
                                "description": "Gerado automaticamente usando dados coletados do OpenALex no perído de 2012 até 2022",
                                "context_by": ["thematic_level_0", "open_access_status"],
                                "default_filter": {"record_type": "article"},
                                "range_filter": {
                                    "filter_name": "year",
                                    "range": {"start": 2012, "end": 2022}
                                }
                            },
                            # Directory
                            {
                                "filters": [],
                                "title": "Número de ações em ciência aberta por área temática e regiões",
                                "facet_by": "action",
                                "description": "Gerado automaticamente usando dados coletados e registrados manualmente por SciELO",
                                "context_by": ["thematic_areas", "regions"],
                                "default_filter": {"record_type": "directory"},
                                "range_filter": None,
                                "fill_range": True,
                                "models": ["infrastructuredirectory", "eventdirectory", "educationdirectory", "policydirectory"]
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
                                    "models": ["infrastructuredirectory", "eventdirectory", "educationdirectory", "policydirectory"]
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
                                "models": ["infrastructuredirectory", "eventdirectory", "educationdirectory", "policydirectory"] 
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
                                "models": ["infrastructuredirectory", "eventdirectory", "educationdirectory", "policydirectory"] 
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
                                "models": ["infrastructuredirectory", "eventdirectory", "educationdirectory", "policydirectory"] 
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
                                "models": ["infrastructuredirectory", "eventdirectory", "educationdirectory", "policydirectory"] 
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
                                "models": ["infrastructuredirectory", "eventdirectory", "educationdirectory", "policydirectory"]
                            }
                        ]
                    }
                ),
                "enabled": False,
                "description": "Essa tarefa tem como responsabilidade gerar os registro de indicadores baseado nos parâmetros definido na chave ``indicators`` da lista de argumentos (Keyword Arguments)",
            },
        ]
    }

    schedule, _ = CrontabSchedule.objects.get_or_create(
        minute="30",
        hour="*",
        day_of_week="*",
        day_of_month="*",
        month_of_year="*",
        timezone=zoneinfo.ZoneInfo("America/Sao_Paulo"),
    )

    for task in tasks.get("tasks"):
        task.update({"crontab": schedule})
        try:
            PeriodicTask.objects.create(**task)
        except django.core.exceptions.ValidationError as e:
            print("Erro on create task: %s, erro: %s" % (task.get("name"), e))
        else:
            print("Task %s created!!!" % task.get("name"))
