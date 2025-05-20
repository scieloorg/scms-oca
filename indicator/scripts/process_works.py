import datetime
import gzip
import logging
import multiprocessing
import os
import sys
import time
import warnings
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse

import orjson
import urllib3
from django.conf import settings
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from tenacity import retry, stop_after_attempt, wait_exponential
from urllib3.exceptions import InsecureRequestWarning


urllib3.disable_warnings(InsecureRequestWarning)

warnings.filterwarnings(
    "ignore",
    message="Connecting to .* using TLS with verify_certs=False is insecure",
    category=Warning,
)

def configure_logger(level: str = "INFO"):
    log_level = getattr(logging, level.upper(), logging.INFO)
    logger = logging.getLogger(__name__)
    if not logger.hasHandlers():
        handler = logging.StreamHandler()
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logger.setLevel(log_level)
    return logger

logger = configure_logger("INFO")

# Pegando a URL completa
es_url = settings.HAYSTACK_CONNECTIONS['es']['URL']  # ex: http://user:pass@host:9200/
parsed_url = urlparse(es_url)

# Extração de partes
ES_HOST = f"{parsed_url.scheme}://{parsed_url.hostname}:{parsed_url.port}"
ES_USER = parsed_url.username or 'elastic'
ES_PASSWORD = parsed_url.password or ''
ES_INDEX = settings.HAYSTACK_CONNECTIONS['es']['INDEX_NAME']
ES_PIPELINE = getattr(settings, 'ES_PIPELINE', ES_INDEX)

es = Elasticsearch(
    ES_HOST,
    basic_auth=(ES_USER, ES_PASSWORD),
    verify_certs=False,
)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10), reraise=True)
def send_log_to_es(log_message, level, id="", log_to_es=True):
    if not log_to_es:
        return
    log_data = {
        "id": id or "",
        "@timestamp": datetime.datetime.now().isoformat(),
        "level": level,
        "message": log_message,
        "application": "opoca_article",
    }
    try:
        es.index(index=f"opoca_logs-{datetime.datetime.now().strftime('%Y-%m-%d')}", id=id or "", body=log_data)
    except Exception as e:
        logger.error(f"Erro ao enviar log para o Elasticsearch: {e}")


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10), reraise=True)
def get_doc_by_search(index, id_value):
    try:
        response = es.search(index=index, q=id_value)
        hits = response.get("hits", {}).get("hits", [])
        return hits[0].get("_source") if hits else None
    except Exception as e:
        logger.error(f"Error retrieving from {index}: {e}")
        return None

@lru_cache(maxsize=100000000)
def get_institution(inst_id):
    return get_doc_by_search(settings.INSTITUTION_INDEX, inst_id)


@lru_cache(maxsize=10000)
def get_country_by_iso_code(country_code):
    return get_doc_by_search(settings.COUNTRY_INDEX, country_code)


@lru_cache(maxsize=10000)
def get_region_info(city):
    return get_doc_by_search(settings.REGION_INDEX, city)


@lru_cache(maxsize=10000)
def get_thematic_area(concept):
    return get_doc_by_search(settings.THEMATIC_AREA_INDEX, concept)

def get_inst_ids(data):
    ids = data.get("corresponding_institution_ids", [])
    return [urlparse(id).path.split("/")[-1] for id in ids if id]


def geo_enrich(data):
    geos = {
        "cities": set(),
        "regions": set(),
        "countries_code": set(),
        "countries_name": set(),
        "countries_alpha_code2": set(),
        "continental_regions": set(),
        "scimago_regions": set(),
        "iso_countries_name": set(),
        "scielo_countries_name": set(),
        "open_alex_regions": set(),
    }
    inst_ids = get_inst_ids(data)
    if inst_ids:
        for inst_id in inst_ids:
            inst = get_institution(inst_id)
            if inst and inst.get("geo"):
                geo = inst.get("geo")
                geos["cities"].add(geo.get("city"))
                geos["countries_code"].add(geo.get("country_code"))
                geos["countries_name"].add(geo.get("country"))
                region_info = get_region_info(geo.get("city"))
                if region_info:
                    geos["regions"].add(region_info.get("regiao"))
                    geos.setdefault("states", set()).add(region_info.get("name"))
                country_info = get_country_by_iso_code(geo.get("country_code"))
                if country_info:
                    geos["countries_alpha_code2"].add(country_info.get("ISO-3166-alpha2-code"))
                    geos["continental_regions"].add(country_info.get("region"))
                    geos["scimago_regions"].add(country_info.get("scimago-region"))
                    geos["iso_countries_name"].add(country_info.get("ISO-country-name"))
                    geos["scielo_countries_name"].add(country_info.get("scielo-country-name"))
                    geos["open_alex_regions"].add(country_info.get("region OpenAlex"))
    data["geos"] = {k: list(v) for k, v in geos.items()}
    return data


def thematic_enrich(data):
    if data.get("concepts"):
        thematic_areas = []
        for concept in data.get("concepts"):
            area = get_thematic_area(concept.get("display_name"))
            if area:
                thematic_areas.append(area)
        tuple_list = [tuple(d.items()) for d in thematic_areas]
        unique_tuples = set(tuple_list)
        thematic_areas = [dict(t) for t in unique_tuples]
        data["thematic_areas"] = thematic_areas
    return data


def bulk_index_documents(docs):
    actions = [
        {"_index": ES_INDEX, "_id": doc["id"], "_source": doc, "pipeline": ES_PIPELINE}
        for doc in docs if doc.get("id")
    ]
    try:
        success, _ = bulk(es, actions, raise_on_error=True)
        logger.info(f"{success} documentos enviados via bulk.")
    except Exception as e:
        logger.error(f"Erro no bulk indexing: {e}")


def process_file(arquivo, start_date=2014, end_date=2025):
    bulk_buffer = []
    try:
        open_func = gzip.open if str(arquivo).endswith(".gz") else open
        with open_func(arquivo, "rb") as works_jsonl:
            for line in works_jsonl:
                try:
                    data = orjson.loads(line)
                    work_id = data.get("id")
                    logger.info(f"Processing work: {work_id} from file: {arquivo}")
                    data = geo_enrich(data)
                    data = thematic_enrich(data)

                    # Transformar counts_by_year em um objeto com anos como chaves
                    if "counts_by_year" in data and isinstance(data["counts_by_year"], list):
                        counts_transformed = {
                            str(item["year"]): item["cited_by_count"]
                            for item in data["counts_by_year"]
                        }
                        data["counts_by_year"] = counts_transformed
                    
                    for field in ["topics", "primary_topic", "abstract_inverted_index"]:
                        data.pop(field, None)
                    if data.get("publication_year") in range(start_date, end_date):
                        bulk_buffer.append(data)
                        if len(bulk_buffer) >= 1000:
                            bulk_index_documents(bulk_buffer)
                            bulk_buffer.clear()
                except orjson.JSONDecodeError as e:
                    logger.error(f"Erro decodificando JSON: {e}")
    except Exception as e:
        logger.error(f"Erro processando arquivo {arquivo}: {e}")
    if bulk_buffer:
        bulk_index_documents(bulk_buffer)


def run(*args):
    """
    Uso com runscript (argumentos posicionais, nessa ordem):

        python manage.py runscript process_works --script-args <data_dir> <limit> <processes> <log_level> <disable_multiprocessing>

    Exemplos:

        # Com multiprocessing ativado
        python manage.py runscript process_works --script-args /Volumes/Data/openalex-slim 1 4 INFO False

        # Sem multiprocessing
        python manage.py runscript process_works --script-args /Volumes/Data/openalex-slim 10 2 DEBUG True

        # Somente o obrigatório (mínimo)
        python manage.py runscript process_works --script-args /Volumes/Data/openalex-slim
    """
    data_dir = args[0] if len(args) > 0 else None
    processes = int(args[2]) if len(args) > 2 and args[2].isdigit() else None
    log_level = args[3] if len(args) > 3 else "INFO"
    disable_multiprocessing = args[4].lower() == "true" if len(args) > 4 else False
    
    if not data_dir:
        print("❌ ERRO: Parâmetro <data_dir> é obrigatório.")
        return

    global logger
    logger = configure_logger(log_level)

    start_time = time.time()
    jsonl_files = list(Path(data_dir).glob("*.jsonl")) + list(Path(data_dir).glob("*.jsonl.gz"))

    logger.info(f"Found {len(jsonl_files)} files to process.")

    if disable_multiprocessing:
        
        for file in jsonl_files:
            process_file(file)
    else:
        num_proc = processes or os.cpu_count()
        logger.info(f"Multiprocessing with {num_proc} processes")
        with multiprocessing.Pool(processes=num_proc) as pool:
            pool.map(process_file, jsonl_files)

    elapsed = time.time() - start_time
    logger.info(f"Finished in {str(datetime.timedelta(seconds=int(elapsed)))}")
