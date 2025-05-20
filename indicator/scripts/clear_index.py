import logging
import sys
from elasticsearch import Elasticsearch
from urllib.parse import urlparse
from django.conf import settings
from datetime import datetime

# Configura logger
def configure_logger(level: str = "INFO"):
    log_level = getattr(logging, level.upper(), logging.INFO)
    logger = logging.getLogger("clear_index")
    if not logger.hasHandlers():
        handler = logging.StreamHandler()
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logger.setLevel(log_level)
    return logger


logger = configure_logger("INFO")

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


def send_log_to_es(message, level, log_to_es=True):
    if not log_to_es:
        return
    try:
        es.index(
            index=f"opoca_logs-{datetime.now().strftime('%Y-%m-%d')}",
            body={
                "@timestamp": datetime.now().isoformat(),
                "level": level,
                "message": message,
                "application": "clear_index",
            },
        )
    except Exception as e:
        logger.warning(f"Não foi possível enviar log para o ES: {e}")


def delete_all_documents(index_name: str, field: str = None, value: str = None):
    try:
        if field and value:
            query = {"term": {field: value}}
            logger.info(f"Deletando documentos de '{index_name}' onde {field} = '{value}'")
        else:
            query = {"match_all": {}}
            logger.info(f"Deletando todos os documentos do índice '{index_name}'")

        response = es.delete_by_query(
            index=index_name,
            body={"query": query},
            conflicts="proceed",
            refresh=True,
            wait_for_completion=True,
            request_timeout=300,
        )
        logger.info(f"Resposta do Elasticsearch: {response}")
        send_log_to_es(f"Delete concluído em {index_name}", "INFO", log_to_es=False)

    except Exception as e:
        logger.error(f"Erro ao deletar documentos de {index_name}: {e}")
        send_log_to_es(f"Erro ao deletar documentos de {index_name}: {e}", "ERROR", log_to_es=False)


def run(*args):
    """
    Uso:
        python manage.py runscript clear_index --script-args <index_name> [field] [value]

    Exemplos:
        # Deletar tudo do índice
        python manage.py runscript clear_index --script-args my_index

        # Deletar apenas documentos filtrando por campo/valor
        python manage.py runscript clear_index --script-args my_index status published
    """
    if len(args) < 1:
        print("❌ ERRO: É necessário pelo menos o nome do índice.")
        return

    index_name = args[0]
    field = args[1] if len(args) > 1 else None
    value = args[2] if len(args) > 2 else None

    delete_all_documents(index_name, field, value)
