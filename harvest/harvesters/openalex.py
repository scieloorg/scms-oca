import gzip
import io
import json
import logging
import re
from datetime import date

from django.conf import settings
from django.utils import timezone

from core.utils.utils import fetch_data
from etl.client import OpenSearchClient
from etl.documents import RawOpenAlexInputDocument
from etl.mapping_silver import SILVER_MAPPING
from etl.transform.standardizer import OpenAlexStandardizer
from etl.world_regions import add_affiliation_world_regions, add_source_world_region
from harvest.exception_logs import ExceptionContext
from harvest.harvesters.common import JSON_HEADERS
from harvest.models import (
    HarvestErrorLogOpenAlex,
    HarvestStatus,
    IndexStatus,
    OpenAlexHarvestRequest,
    OpenAlexRequestKind,
)

logger = logging.getLogger(__name__)

S3_BUCKET_PREFIX = "s3://openalex/"
UPDATED_DATE_RE = re.compile(r"updated_date=(\d{4}-\d{2}-\d{2})")


def s3_url_to_https(s3_url):
    return (
        f"{settings.OPENALEX_SNAPSHOT_BASE_URL.rstrip('/')}/"
        f"{s3_url.removeprefix(S3_BUCKET_PREFIX)}"
    )


def parse_updated_date_from_url(url):
    return date.fromisoformat(UPDATED_DATE_RE.search(url).group(1))


def iter_part_files(manifest, from_updated_date):
    """
    Lista e ordena as parts do manifest elegíveis para coleta.

    Filtra entradas com ``updated_date`` maior ou igual a ``from_updated_date``
    e enriquece cada item com URL HTTPS e metadados do manifest.

    Parâmetros:
        manifest (dict): Conteúdo JSON do manifest OpenAlex (``date`` + ``files``).
        from_updated_date (str ou date): Data mínima da partição a considerar.

    Retorna:
        list[dict]: Parts ordenadas por ``updated_date`` e URL, cada uma com
        ``s3_url``, ``https_url``, ``updated_date`` e ``record_count``.
    """
    from_date = date.fromisoformat(str(from_updated_date))
    parts = [
        {
            "s3_url": entry["url"],
            "https_url": s3_url_to_https(entry["url"]),
            "updated_date": parse_updated_date_from_url(entry["url"]),
            "record_count": entry["meta"]["record_count"],
            "content_length": entry.get("meta", {}).get("content_length"),
        }
        for entry in manifest["files"]
        if parse_updated_date_from_url(entry["url"]) >= from_date
    ]
    return sorted(parts, key=lambda part: (part["updated_date"], part["https_url"]))


def iter_gzip_jsonl_works(fileobj, publication_year_from, is_xpac):
    """
    Lê JSONL gzip de um file-like e produz works que passam nos filtros.
    """
    with gzip.GzipFile(fileobj=fileobj) as gzip_file:
        for line_number, line in enumerate(gzip_file, start=1):
            if not line or not line.strip():
                continue
            try:
                work = json.loads(line)
            except json.JSONDecodeError as exc:
                logger.warning(
                    f"Linha {line_number} inválida no gzip OpenAlex: {exc}"
                )
                continue

            publication_year = work.get("publication_year")
            if publication_year is None or publication_year < publication_year_from:
                continue
            if is_xpac is not None and work.get("is_xpac", False) is not is_xpac:
                continue
            yield work


def iter_part_works(url, publication_year_from, is_xpac):
    """
    Baixa uma part gzip/JSONL e produz os works OpenAlex elegíveis.

    Aplica ``publication_year >= publication_year_from`` e, quando informado,
    o filtro ``is_xpac`` durante a leitura.

    Parâmetros:
        url (str): URL HTTPS da part no snapshot S3.
        publication_year_from (int): Ano mínimo de publicação.
        is_xpac (bool ou None): Quando definido, exige ``work["is_xpac"]`` igual
            a este valor; campo ausente é tratado como ``False``. ``None``
            desativa o filtro.

    Produz:
        dict: Work OpenAlex bruto que passou pelos filtros.
    """
    payload = fetch_data(
        url,
        headers=JSON_HEADERS,
        json=False,
        timeout=settings.OPENALEX_PART_FETCH_TIMEOUT,
        verify=True,
    )
    yield from iter_gzip_jsonl_works(
        io.BytesIO(payload),
        publication_year_from,
        is_xpac,
    )


def index_openalex_batch(client, documents):
    """
    Indexa works no write alias OpenAlex.

    O mesmo ``_id`` no índice de escrita substitui o documento existente.
    """
    actions = []
    write_alias = settings.ETL_OPENALEX_ONLY_WRITE_ALIAS

    for openalex_id, source in documents:
        actions.extend(
            [
                {
                    "index": {
                        "_index": write_alias,
                        "_id": openalex_id,
                    }
                },
                source,
            ]
        )

    response = client.client.bulk(body=actions)
    if response.get("errors"):
        failures = [
            item.get("index", {})
            for item in response["items"]
            if item.get("index", {}).get("status", 200) >= 400
        ]
        first_error = failures[0].get("error") if failures else None
        raise RuntimeError(
            f"Falha ao indexar {len(failures)} documentos OpenAlex: {first_error}"
        )

    return len(documents)


def fetch_manifest(user, publication_year_from, is_xpac):
    """
    Busca o manifest de works do snapshot OpenAlex.

    Em caso de falha na requisição, registra ``OpenAlexHarvestRequest`` e log de
    erro, sem relançar a exceção.

    Parâmetros:
        user: Usuário responsável pela coleta (campo ``creator``).
        publication_year_from (int): Ano mínimo usado nos registros de log.
        is_xpac (bool ou None): Valor do filtro ``is_xpac`` usado nos registros.

    Retorna:
        dict ou None: Manifest JSON em sucesso; ``None`` se a requisição falhar.
    """
    try:
        return fetch_data(
            settings.OPENALEX_WORKS_MANIFEST_URL,
            headers=JSON_HEADERS,
            json=True,
            timeout=60,
            verify=True,
        )
    except Exception as exc:
        logger.error(f"Erro ao buscar manifest OpenAlex: {exc}")
        manifest_request = OpenAlexHarvestRequest.objects.create(
            creator=user,
            request_url=settings.OPENALEX_WORKS_MANIFEST_URL,
            request_kind=OpenAlexRequestKind.MANIFEST,
            publication_year_from=publication_year_from,
            is_xpac=is_xpac,
            harvest_status=HarvestStatus.IN_PROGRESS,
            requested_at=timezone.now(),
        )
        manifest_error = ExceptionContext(
            harvest_object=manifest_request,
            log_model=HarvestErrorLogOpenAlex,
            fk_field="openalex_request",
        )
        manifest_error.add_exception(
            exception=exc,
            field_name="manifest",
            context_data={"url": settings.OPENALEX_WORKS_MANIFEST_URL},
        )
        manifest_error.save_to_db()
        manifest_error.mark_status_harvest()
        return None


def get_or_reuse_part_request(part, user, publication_year_from, is_xpac):
    """
    Recupera o registro incompleto da part ou cria um novo.

    Se já existir uma part com a mesma URL e status diferente de ``success``,
    reutiliza esse registro em vez de criar outro.
    """
    defaults = {
        "updated_date": part["updated_date"],
        "publication_year_from": publication_year_from,
        "is_xpac": is_xpac,
        "manifest_record_count": part["record_count"],
        "harvest_status": HarvestStatus.IN_PROGRESS,
        "index_status": IndexStatus.PENDING,
        "document_ids": [],
        "result_count": 0,
        "requested_at": timezone.now(),
    }
    part_request = OpenAlexHarvestRequest.get_incomplete_part(part["https_url"])
    if part_request is None:
        return OpenAlexHarvestRequest.objects.create(
            creator=user,
            request_url=part["https_url"],
            request_kind=OpenAlexRequestKind.PART,
            **defaults,
        )

    logger.info(
        f"Reutilizando registro da part {part['https_url']} "
        f"(id={part_request.pk}, harvest_status={part_request.harvest_status}, "
        f"index_status={part_request.index_status})"
    )
    for field, value in defaults.items():
        setattr(part_request, field, value)
    part_request.updated_by = user
    part_request.save()
    return part_request


def get_or_reuse_manifest_request(
    user,
    manifest_date,
    publication_year_from,
    is_xpac,
):
    """
    Recupera o manifest incompleto da mesma data ou cria um novo.
    """
    defaults = {
        "updated_date": manifest_date,
        "publication_year_from": publication_year_from,
        "is_xpac": is_xpac,
        "harvest_status": HarvestStatus.IN_PROGRESS,
        "requested_at": timezone.now(),
    }
    manifest_request = OpenAlexHarvestRequest.get_incomplete_manifest(manifest_date)
    if manifest_request is None:
        return OpenAlexHarvestRequest.objects.create(
            creator=user,
            request_url=settings.OPENALEX_WORKS_MANIFEST_URL,
            request_kind=OpenAlexRequestKind.MANIFEST,
            **defaults,
        )

    logger.info(
        f"Reutilizando registro do manifest {manifest_date} "
        f"(id={manifest_request.pk}, harvest_status={manifest_request.harvest_status})"
    )
    for field, value in defaults.items():
        setattr(manifest_request, field, value)
    manifest_request.updated_by = user
    manifest_request.save()
    return manifest_request


def _transform_work(work, standardizer):
    input_document = RawOpenAlexInputDocument.from_raw(work)
    silver_document = standardizer.run(input_document)
    source = silver_document.to_index_dict()
    add_source_world_region(source)
    add_affiliation_world_regions(source)

    openalex_id = silver_document.openalex_id
    if not openalex_id:
        raise ValueError("Documento OpenAlex padronizado sem openalex_id")
    return openalex_id, source


def _flush_batch(client, part_request, batch):
    """
    Indexa o lote no write alias OpenAlex.

    Marca o início da indexação no request apenas no primeiro flush
    (``index_status`` ainda ``PENDING``).
    """
    if part_request.index_status == IndexStatus.PENDING:
        part_request.mark_as_index_in_progress()
    return index_openalex_batch(client, batch)


def _index_part_works(
    part,
    part_request,
    publication_year_from,
    is_xpac,
    batch_size,
    client,
):
    """
    Transforma os works elegíveis da part e indexa em lotes de ``batch_size``.

    Retorna:
        tuple[int, int]: Quantidade de documentos indexados e de works
        ignorados por erro de transformação.
    """
    standardizer = OpenAlexStandardizer()
    batch = []
    indexed_count = 0
    skipped_count = 0

    for work in iter_part_works(
        part["https_url"],
        publication_year_from,
        is_xpac,
    ):
        try:
            batch.append(_transform_work(work, standardizer))
        except Exception as exc:
            skipped_count += 1
            logger.warning(
                f"Work OpenAlex ignorado na part {part['https_url']}: {exc}"
            )
            continue

        if len(batch) == batch_size:
            indexed_count += _flush_batch(client, part_request, batch)
            batch = []
            logger.info(
                f"Part {part['https_url']}: {indexed_count} documentos indexados"
            )

    if batch:
        indexed_count += _flush_batch(client, part_request, batch)

    return indexed_count, skipped_count


def _handle_part_error(part_request, part, exc):
    """
    Registra o erro da part e marca os status de falha.

    Marca ``index_status`` como ``failed`` apenas se a indexação chegou a
    começar (``IN_PROGRESS``).
    """
    part_error = ExceptionContext(
        harvest_object=part_request,
        log_model=HarvestErrorLogOpenAlex,
        fk_field="openalex_request",
    )
    part_error.add_exception(
        exception=exc,
        field_name="part",
        context_data={"url": part["https_url"]},
    )
    part_error.save_to_db()
    if part_request.index_status == IndexStatus.IN_PROGRESS:
        part_request.mark_as_index_failed()
    part_error.mark_status_harvest()


def process_part(part, user, publication_year_from, is_xpac, batch_size, client):
    """
    Coleta uma part do snapshot e persiste o log da requisição.

    Recupera ``OpenAlexHarvestRequest`` (kind ``part``) quando a URL já foi
    registrada sem sucesso, transforma e indexa cada work filtrado, atualiza
    ``result_count``, e marca sucesso ou falha.

    Parâmetros:
        part (dict): Item retornado por ``iter_part_files``.
        user: Usuário responsável pela coleta.
        publication_year_from (int): Ano mínimo de publicação.
        is_xpac (bool ou None): Filtro opcional de works curados XPAC.
        batch_size (int): Tamanho dos lotes de indexação no OpenSearch.
        client (OpenSearchClient): Cliente reutilizado na execução.

    Retorna:
        bool: ``True`` se a part foi coletada com sucesso; ``False`` em erro.
    """
    part_request = get_or_reuse_part_request(
        part,
        user,
        publication_year_from,
        is_xpac,
    )
    logger.info(
        f"Processando part {part['https_url']} "
        f"(manifest_record_count={part['record_count']}, "
        f"content_length={part.get('content_length')})"
    )
    try:
        indexed_count, skipped_count = _index_part_works(
            part,
            part_request,
            publication_year_from,
            is_xpac,
            batch_size,
            client,
        )
    except Exception as exc:
        logger.error(f"Erro ao buscar part OpenAlex {part['https_url']}: {exc}")
        _handle_part_error(part_request, part, exc)
        return False

    if part_request.index_status == IndexStatus.IN_PROGRESS:
        client.rollover(
            write_alias=settings.ETL_OPENALEX_ONLY_WRITE_ALIAS,
            public_alias=settings.ETL_PUBLIC_ALIAS,
            mapping=SILVER_MAPPING,
            max_size=settings.ETL_SILVER_ROLLOVER_MAX_SIZE,
        )

    part_request.result_count = indexed_count
    part_request.save(update_fields=["result_count", "updated"])
    part_request.mark_as_success()
    part_request.mark_as_indexed()
    logger.info(
        f"Part coletada: {part['https_url']} "
        f"({indexed_count} indexados com "
        f"publication_year>={publication_year_from}, is_xpac={is_xpac}; "
        f"{skipped_count} ignorados)"
    )
    return True


def process_manifest_parts(
    manifest_request,
    parts,
    user,
    publication_year_from,
    is_xpac,
    batch_size,
    client,
):
    """
    Processa as parts pendentes de um manifest já registrado.

    Pula URLs com coleta anterior em ``success``. Reutiliza registros de parts
    com status diferente de ``success``. Interrompe e marca o manifest
    como ``failed`` na primeira part com erro. Marca o manifest como ``success``
    somente quando todas as parts elegíveis estão concluídas.

    Parâmetros:
        manifest_request (OpenAlexHarvestRequest): Registro do manifest em andamento.
        parts (iterable): Parts retornadas por ``iter_part_files``.
        user: Usuário responsável pela coleta.
        publication_year_from (int): Ano mínimo de publicação.
        is_xpac (bool ou None): Filtro opcional de works curados XPAC.
        batch_size (int): Tamanho dos lotes de indexação no OpenSearch.
        client (OpenSearchClient): Cliente reutilizado na execução.
    """
    completed_urls = OpenAlexHarvestRequest.get_completed_part_urls()

    for part in parts:
        if part["https_url"] in completed_urls:
            logger.info(
                f"Part já coletada com sucesso, pulando: {part['https_url']}"
            )
            continue

        if not process_part(
            part,
            user,
            publication_year_from,
            is_xpac,
            batch_size,
            client,
        ):
            manifest_request.mark_as_failed()
            return

        completed_urls.add(part["https_url"])

    manifest_completed = all(
        part["https_url"] in completed_urls
        for part in parts
    )
    if manifest_completed:
        manifest_request.mark_as_success()


def harvest_openalex_works(
    user,
    publication_year_from,
    from_updated_date,
    is_xpac=False,
    batch_size=1000,
):
    """
    Orquestra a coleta incremental do snapshot OpenAlex (works).

    Fluxo: busca manifest → verifica se já foi processado → registra manifest →
    coleta parts pendentes desde ``from_updated_date``, aplicando filtros de ano
    e ``is_xpac``, e indexa os works padronizados no silver OpenAlex.

    Parâmetros:
        user: Usuário responsável pela coleta.
        publication_year_from (int): Ano mínimo de publicação dos works.
        from_updated_date (str ou date): Data mínima das parts S3 a considerar.
        is_xpac (bool ou None, opcional): Filtro de works curados XPAC.
            ``False`` (padrão) indexa works sem XPAC; campo ausente no snapshot
            público conta como ``False``.
        batch_size (int, opcional): Tamanho dos lotes de indexação.
    """
    logger.info(
        f"Iniciando coleta OpenAlex snapshot a partir de {from_updated_date}, "
        f"publication_year>={publication_year_from}, is_xpac={is_xpac}, "
        f"batch_size={batch_size}"
    )
    client = OpenSearchClient()
    client.ensure_rollover_index(
        index_prefix=settings.ETL_OPENALEX_ONLY_INDEX_PATTERN,
        write_alias=settings.ETL_OPENALEX_ONLY_WRITE_ALIAS,
        public_alias=settings.ETL_PUBLIC_ALIAS,
        mapping=SILVER_MAPPING,
    )

    manifest = fetch_manifest(user, publication_year_from, is_xpac)
    if manifest is None:
        return

    manifest_date = date.fromisoformat(manifest["date"])
    manifest_processed = OpenAlexHarvestRequest.objects.filter(
        request_kind=OpenAlexRequestKind.MANIFEST,
        updated_date=manifest_date,
        harvest_status=HarvestStatus.SUCCESS,
    ).exists()
    if manifest_processed:
        logger.info(f"Manifest OpenAlex {manifest_date} já processado.")
        return

    manifest_request = get_or_reuse_manifest_request(
        user=user,
        manifest_date=manifest_date,
        publication_year_from=publication_year_from,
        is_xpac=is_xpac,
    )
    process_manifest_parts(
        manifest_request=manifest_request,
        parts=iter_part_files(manifest, from_updated_date),
        user=user,
        publication_year_from=publication_year_from,
        is_xpac=is_xpac,
        batch_size=batch_size,
        client=client,
    )
