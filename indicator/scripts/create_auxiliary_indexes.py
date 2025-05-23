import os
import orjson
from elasticsearch import Elasticsearch
from urllib.parse import urlparse
from django.conf import settings
from pathlib import Path


def run():
    print("Iniciando upload de dados para Elasticsearch...")

    # Definir o diretório base (onde estão os arquivos JSON)
    base_dir = Path(__file__).resolve().parent.parent.parent / "fixtures" / "auxiliary_indexes"

    # Ler os arquivos
    with open(base_dir / "brazilian_cities_states_regions.json", "rb") as f:
        BRA_CITIES_STATES_REGIONS = orjson.loads(f.read())

    with open(base_dir / "regions.json", "rb") as f:
        CONTINENTAL_REGIONS = orjson.loads(f.read())

    with open(base_dir / "thematics.json", "rb") as f:
        THEMATIC_AREAS = orjson.loads(f.read())

    # Conecta ao Elasticsearch a partir do settings
    es_url = settings.HAYSTACK_CONNECTIONS["es"]["URL"]
    parsed_url = urlparse(es_url)
    ES_HOST = f"{parsed_url.scheme}://{parsed_url.hostname}:{parsed_url.port}"
    ES_USER = parsed_url.username or "elastic"
    ES_PASSWORD = parsed_url.password or ""

    es = Elasticsearch(
        ES_HOST,
        basic_auth=(ES_USER, ES_PASSWORD),
        verify_certs=settings.HAYSTACK_CONNECTIONS["es"].get("KWARGS", {}).get("verify_certs", False)
    )

    # Upload dos dados de cidades, estados e regiões
    print("Subindo dados de regiões brasileiras...")
    for region in BRA_CITIES_STATES_REGIONS.get("estados", []):
        es.index(index="regionsbra", id=region["sigla"], document=region)
    print("Regiões brasileiras carregadas.")

    # Upload dos dados de regiões continentais
    print("Subindo dados de regiões continentais...")
    for regioncon in CONTINENTAL_REGIONS:
        es.index(index="regionscon", id=regioncon["ISO-3166-alpha2-code"], document=regioncon)
    print("Regiões continentais carregadas.")

    # Upload das áreas temáticas
    print("Subindo dados de áreas temáticas...")
    for key, thematic in THEMATIC_AREAS.items():
        thematic["id"] = key
        es.index(index="thematicareas", id=key, document=thematic)
    print("Áreas temáticas carregadas.")

    print("Processo concluído com sucesso.")
