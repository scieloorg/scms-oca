"""
Serviço de transformação de dados raw para bronze no OpenSearch.
Utiliza scripts Painless configurados via interface.
"""
import json
import logging
from typing import Any, Optional

from search_gateway.client import get_opensearch_client

logger = logging.getLogger(__name__)


client = get_opensearch_client()

def index_exists(index_name):
    """
    Verifica se um índice existe no OpenSearch.

    Mantém o comportamento simples (True/False) para facilitar reuso.
    """
    return bool(client.indices.exists(index=index_name))


def _missing_index_error(source_index, dest_index):
    return {
        "status": "error",
        "message": (
            "O indice source ou destino: "
            f"{source_index} / {dest_index} não existe no opensearch"
        ),
    }


def _ensure_indices_exist(source_index, dest_index):
    if not index_exists(source_index) or not index_exists(dest_index):
        return _missing_index_error(source_index, dest_index)
    return None


def _parse_query_script(query_script, identifier=None):
    """
    Retorna um dict de query (para `source.query` do reindex).

    - `query_script` pode ser `str` (JSON) ou `dict`.
    - Se `identifier` for informado, substitui placeholder `{{identifier}}`.
    """
    if query_script is None or query_script == "":
        raise ValueError("query_script vazio")

    if isinstance(query_script, dict):
        query = query_script
    elif isinstance(query_script, str):
        raw = query_script
        if identifier:
            raw = raw.replace("{{identifier}}", identifier).replace(
                "{{ identifier }}", identifier
            )
        query = json.loads(raw)
    else:
        raise TypeError("query_script deve ser str (JSON) ou dict")

    if not isinstance(query, dict):
        raise ValueError("query_script precisa ser um JSON object (dict)")
    return query


def _build_reindex_body(
    *,
    source_index,
    dest_index,
    transform_script,
    query_script=None,
    identifier=None,
):
    body = {
        "source": {"index": source_index},
        "dest": {"index": dest_index},
        "script": {"lang": "painless", "source": transform_script},
    }

    if identifier:
        if query_script:
            body["source"]["query"] = _parse_query_script(
                query_script=query_script,
                identifier=identifier,
            )
        else:
            body["source"]["query"] = {"term": {"_id": identifier}}
        return body

    if query_script:
        body["source"]["query"] = _parse_query_script(query_script=query_script)

    return body


def _format_reindex_counts(response):
    total = int(response.get("total", 0) or 0)
    updated = int(response.get("updated", 0) or 0)
    created = int(response.get("created", 0) or 0)
    return total, created, updated


def _run_reindex(*, body, log_prefix, error_context):
    try:
        logger.info(log_prefix)
        response = client.reindex(body=body, refresh=True)
        total, created, updated = _format_reindex_counts(response)
        logger.info(
            "Transformação concluída: total=%s, created=%s, updated=%s",
            total,
            created,
            updated,
        )
        return {
            "status": "success",
            "message": (
                f"Transformação concluída: total={total}, created={created}, updated={updated}"
            ),
        }
    except Exception as exc:
        logger.error("Erro ao transformar documento %s: %s", error_context, exc)
        return {
            "status": "error",
            "message": f"Erro ao transformar documento {error_context}: {exc}",
        }


def transform_document(script, identifier=None):
    """
    Usado para transformação automática após indexação de um novo documento.

    Args:
        script: Instância do TransformationScript
        identifier: ID do documento a transformar

    Returns:
        Dict com status e mensagem da operação
    """
    missing = _ensure_indices_exist(script.source_index, script.dest_index)
    if missing:
        return missing

    try:
        body = _build_reindex_body(
            source_index=script.source_index,
            dest_index=script.dest_index,
            transform_script=script.transform_script,
            query_script=getattr(script, "query_script", None),
            identifier=identifier,
        )
    except Exception as exc:
        return {"status": "error", "message": f"Query JSON inválida: {exc}"}

    result = _run_reindex(
        body=body,
        log_prefix=(
            f"Transformando documento {identifier} de {script.source_index} para {script.dest_index}"
        ),
        error_context=str(identifier),
    )
    if result.get("status") == "success":
        result["message"] = f"Documento {identifier} transformado: {result.get('message', '')}"
    return result


def transform_after_indexing(instance, model_name):
    """
    Função auxiliar para ser chamada após indexação.
    Busca o TransformationScript pelo harvest_model e executa a transformação.

    Args:
        instance: Instância do modelo (HarvestedBooks, HarvestedPreprint, etc)
        model_name: Nome da classe do modelo

    Returns:
        Dict com status e mensagem da operação
    """
    from .models import TransformationScript

    harvest_model_key = model_name
    if model_name == "HarvestedSciELOData":
        type_data = getattr(instance, "type_data", None)
        if type_data:
            harvest_model_key = f"{model_name}_{type_data}"

    script = TransformationScript.objects.filter(
        harvest_model=harvest_model_key,
        is_active=True
    ).first()

    if not script:
        logger.info(
            "Nenhum script de transformação ativo encontrado para %s",
            harvest_model_key
        )
        return {"status": "skip", "message": f"Nenhum script ativo encontrado para {harvest_model_key}"}

    identifier = getattr(instance, "identifier", None)
    if not identifier:
        return {"status": "error", "message": "Instância em identifiesr; não é possível transformar."}

    return transform_document(script, instance.identifier)
