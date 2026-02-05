"""
Serviço de transformação de dados raw para bronze no OpenSearch.
Utiliza scripts Painless configurados via interface.
"""
import json
import logging

from search_gateway.client import get_opensearch_client

logger = logging.getLogger(__name__)


client = get_opensearch_client()

def check_if_indice_exists(index_name):
    if not client.indices.exists(index=index_name):
        return False
    return True


def transform_single_document(instance) -> bool:
    """
    Transforma um único documento do índice raw para bronze.

    Args:
        identifier: ID do documento a transformar
        source_type: Tipo de fonte (books, preprint, scielo_data)
        script: Script de transformação (opcional, busca automaticamente se não fornecido)

    Returns:
        True se a transformação foi bem sucedida, False caso contrário
    """
    if not check_if_indice_exists(instance.source_index) or not check_if_indice_exists(instance.dest_index):
        return {"status": "error", "message": f"O indice source ou destino: {instance.source_index} / {instance.dest_index} não existe no opensearch"}

    try:
        body = {
            "source": {
                "index": instance.source_index,
            },
            "dest": {
                "index": instance.dest_index,
            },
            "script": {
                "lang": "painless",
                "source": instance.transform_script,
            },
        }
        if instance.query_script:
            body["source"]["query"] = json.loads(instance.query_script)
        
        logger.info(
            f"Transformando documento de {instance.source_index} para {instance.dest_index}"
        )

        response = client.reindex(body=body, refresh=True)

        total = response.get("total", 0)
        updated = response.get("updated", 0)
        created = response.get("created", 0)

        logger.info(f"Transformação concluída: total={total}, created={created}, updated={updated}")
        return {"status": "success", "message": f"Transformação concluída: total={total}, created={created}, updated={updated}"}

    except Exception as exc:
        logger.error(f"Erro ao transformar documento {instance.source_index}: {exc}")
        return {"status": "error", "message": f"Erro ao transformar documento {instance.source_index}: {exc}"}


def transform_after_indexing(instance, model_name: str) -> bool:
    """
    Função auxiliar para ser chamada após indexação.
    Determina o source_type a partir do model e executa a transformação.

    Args:
        instance: Instância do modelo (HarvestedBooks, etc)
        model_name: Nome da classe do modelo

    Returns:
        True se a transformação foi bem sucedida
    """
    if instance and not instance.transform_script and not instance.source_index and not instance.dest_index:
        logger.warning("Model %s não possui source_type mapeado", model_name)
        return {"status": "error", "message": "Dados do indice insuficiente"}

    return transform_single_document(
        instance
    )
