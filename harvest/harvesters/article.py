import logging
from datetime import datetime, time

from django.conf import settings
from django.utils import timezone
from django.utils.dateparse import parse_date

from core.utils.utils import fetch_data
from harvest.bronze_transform import transform_indexed_page
from harvest.exception_logs import ExceptionContext
from harvest.harvesters.common import build_url
from harvest.models import HarvestedArticle, HarvestErrorLogArticle

logger = logging.getLogger(__name__)


def _articlemeta_base_url():
    return getattr(settings, "ARTICLEMETA_BASE_URL", "https://articlemeta.scielo.org").rstrip("/")


def article_identifier(code, collection):
    if not code or not collection:
        raise ValueError("Article code and collection are required.")

    return f"{collection}:{code}"


def fetch_article_identifiers_page(
    limit=100,
    offset=0,
    from_date=None,
    until_date=None,
    collection=None,
    headers=None,
):
    """
    Busca identificadores de artigos da API ArticleMeta.

    Parâmetros:
        limit (int, opcional): Número máximo de artigos a serem retornados na consulta. Default: 100.
        offset (int, opcional): Posição inicial (offset) para paginação. Default: 0.
        from_date (str ou None, opcional): Data inicial de coleta dos artigos, no formato 'YYYY-MM-DD'. Default: None.
        until_date (str ou None, opcional): Data final de coleta dos artigos, no formato 'YYYY-MM-DD'. Default: None.
        collection (str ou None, opcional): Código da coleção a ser filtrada (ex: 'scl'). Default: None.
        headers (dict ou None, opcional): Headers HTTP personalizados para a requisição. Default: None.

    Retorna:
        tuple:
            - Lista de objetos identificadores de artigos retornados pela API.
            - Dicionário de metadados da resposta (ex: paginação).

    Raises:
        Pode relançar exceções vindas de fetch_data em caso de erro na requisição.
    """
    params = {
        "limit": limit,
        "offset": offset,
    }
    if from_date:
        params["from"] = from_date
    if until_date:
        params["until"] = until_date
    if collection:
        params["collection"] = collection

    url = build_url(f"{_articlemeta_base_url()}/api/v1/article/identifiers/", params)
    payload = fetch_data(url, headers=headers, json=True, timeout=60, verify=True)
    objects = payload.get("objects", [])
    return objects, payload.get("meta", {})


def fetch_article_detail(code, collection=None, headers=None):
    """
    Busca detalhes de um artigo específico na API ArticleMeta.

    Parâmetros:
        code (str): Código do artigo, único dentro da coleção.
        collection (str ou None, opcional): Código da coleção do artigo (ex: 'scl'). Default: None.
        headers (dict ou None, opcional): Headers HTTP personalizados para a requisição. Default: None.

    Retorna:
        dict: Objeto representando os detalhes do artigo retornado pela API.

    Raises:
        Pode relançar exceções vindas de fetch_data em caso de erro na requisição.
        ValueError: Se a resposta não for um dicionário com a chave "article".
    """
    params = {"code": code}
    if collection:
        params["collection"] = collection
    url = build_url(f"{_articlemeta_base_url()}/api/v1/article/", params)
    payload = fetch_data(url, headers=headers, json=True, timeout=60, verify=True)
    payload.pop("citations", None)
    return payload

def harvest_articles(
    user,
    limit=100,
    offset=0,
    from_date=None,
    until_date=None,
    collection=None,
):
    logger.info(f"Iniciando coleta ArticleMeta a partir do offset {offset}")

    while True:
        try:
            items, _meta = fetch_article_identifiers_page(
                limit=limit,
                offset=offset,
                from_date=from_date,
                until_date=until_date,
                collection=collection,
            )
        except Exception as exc:
            logger.error(f"Erro ao buscar página ArticleMeta (offset={offset}): {exc}")
            break

        if not items:
            logger.info("Nenhum artigo retornado. Finalizando coleta.")
            break

        page_ids = []
        for item in items:
            try:
                harvested_obj = harvest_single_article_item(
                    item=item, user=user, collection=collection
                )
                if harvested_obj and harvested_obj.is_indexed():
                    page_ids.append(harvested_obj.identifier)
            except Exception as exc:
                logger.error(f"Erro ao persistir artigo ArticleMeta: {exc}")

        if page_ids:
            transform_indexed_page("HarvestedArticle", page_ids)

        offset += limit
        if len(items) < limit:
            break


def harvest_single_article_item(item, user, collection=None):
    code = item.get("code")
    collection = item.get("collection") or collection
    article_identifier(code, collection)

    try:
        article_payload = fetch_article_detail(
            code=code,
            collection=collection,
        )
    except Exception as exc:
        return record_article_failure(
            user=user,
            code=code,
            collection=collection,
            exception=exc,
            field_name="get_article",
            context_data=item,
        )
    return persist_article(
        user=user,
        code=code,
        collection=collection,
        article_payload=article_payload,
    )


def record_article_failure(
    user, code, collection, exception, field_name, context_data=None
):
    identifier = article_identifier(code, collection)
    harvested_obj, _created = HarvestedArticle.objects.get_or_create(
        identifier=identifier,
        defaults={"creator": user},
    )
    harvested_obj.mark_as_in_progress()
    exc_context = ExceptionContext(
        harvest_object=harvested_obj,
        log_model=HarvestErrorLogArticle,
        fk_field="article",
    )
    exc_context.add_exception(
        exception=exception,
        field_name=field_name,
        context_data=context_data or {"code": code, "collection": collection},
    )
    exc_context.save_to_db()
    exc_context.mark_status_harvest()
    return harvested_obj


def harvest_single_article_code(code, user, collection):
    article_identifier(code, collection)
    article_payload = fetch_article_detail(code=code, collection=collection)
    harvested_obj = persist_article(
        user=user,
        code=code,
        collection=collection,
        article_payload=article_payload,
    )
    if harvested_obj and harvested_obj.is_indexed():
        transform_indexed_page("HarvestedArticle", [harvested_obj.identifier])
    return harvested_obj


def persist_article(user, code, collection, article_payload):
    identifier = article_identifier(code, collection)

    harvested_obj, _created = HarvestedArticle.objects.get_or_create(
        identifier=identifier,
        defaults={"creator": user},
    )
    harvested_obj.mark_as_in_progress()

    exc_context = ExceptionContext(
        harvest_object=harvested_obj,
        log_model=HarvestErrorLogArticle,
        fk_field="article",
    )

    try:
        if not article_payload:
            raise ValueError("Article payload is empty or invalid.")

        harvested_obj.source_url = build_url(
            f"{_articlemeta_base_url()}/api/v1/article/",
            {"code": code, "collection": collection},
        )
        harvested_obj.raw_data = article_payload
        harvested_obj.datestamp = parse_article_datestamp(article_payload)
        harvested_obj.last_harvest_attempt = timezone.now()
        harvested_obj.save(
            update_fields=[
                "source_url",
                "raw_data",
                "datestamp",
                "last_harvest_attempt",
            ]
        )
    except Exception as exc:
        exc_context.add_exception(
            exception=exc,
            field_name="raw_data",
            context_data={"code": code, "collection": collection},
        )

    exc_context.save_to_db()
    exc_context.mark_status_harvest()
    return harvested_obj


def parse_article_datestamp(raw_data):
    value = raw_data.get("processing_date") or ""

    parsed_date = parse_date(str(value))
    if parsed_date:
        return timezone.make_aware(datetime.combine(parsed_date, time.min))
    return None
