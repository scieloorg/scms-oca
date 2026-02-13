import logging

from django.conf import settings
from django.utils.translation import gettext as _
from opensearchpy.helpers import bulk

from search_gateway.client import get_opensearch_client

logger = logging.getLogger(__name__)


def parse_script_args(args):
    if not args:
        return None, 200, False

    index_name = args[0]
    batch_size = int(args[1]) if len(args) > 1 else 200
    refresh = len(args) > 2 and str(args[2]).lower() == "true"
    return index_name, batch_size, refresh


def to_iso(value):
    return value.isoformat() if value else None


def as_label(value):
    return str(value) if value else None


def thematic_levels_from_obj(obj):
    level_0 = set()
    level_1 = set()
    level_2 = set()

    for thematic_area in obj.thematic_areas.all():
        if thematic_area.level0:
            level_0.add(thematic_area.level0.strip())
        if thematic_area.level1:
            level_1.add(thematic_area.level1.strip())
        if thematic_area.level2:
            level_2.add(thematic_area.level2.strip())

    return sorted(level_0), sorted(level_1), sorted(level_2)


def _country_name(country):
    if not country:
        return None
    return getattr(country, "name", None) or getattr(country, "name_pt", None) or str(country)


def locations_from_related(related_manager, location_attr=None):
    countries = set()
    cities = set()
    states = set()
    regions = set()

    if related_manager is None:
        return sorted(countries), sorted(cities), sorted(states), sorted(regions)

    for related_obj in related_manager.all():
        location_obj = (
            getattr(related_obj, location_attr, None) if location_attr else related_obj
        )
        if not location_obj:
            continue

        country = _country_name(getattr(location_obj, "country", None))
        city = getattr(getattr(location_obj, "city", None), "name", None)
        state_obj = getattr(location_obj, "state", None)
        state = getattr(state_obj, "name", None)
        region = getattr(state_obj, "region", None)

        if country:
            countries.add(country)
        if city:
            cities.add(city)
        if state:
            states.add(state)
        if region:
            regions.add(region)

    return sorted(countries), sorted(cities), sorted(states), sorted(regions)


def build_disclaimer(obj):
    if obj.institutional_contribution == settings.DIRECTORY_DEFAULT_CONTRIBUTOR:
        return None

    message = _("Conteúdo publicado sem moderação / contribuição de %s")
    if obj.updated_by:
        return (
            message % obj.institutional_contribution
            if not obj.updated_by.is_staff and obj.record_status == "PUBLISHED"
            else None
        )

    if obj.creator:
        return (
            message % obj.institutional_contribution
            if not obj.creator.is_staff and obj.record_status == "PUBLISHED"
            else None
        )

    return None


def build_common_directory_doc(
    obj,
    *,
    directory_type,
    scope_label,
    source_value,
    related_manager_attr,
    related_names_field="institutions",
    geo_manager_attr=None,
    geo_location_attr="location",
    include_disclaimer=True,
):
    level_0, level_1, level_2 = thematic_levels_from_obj(obj)
    related_manager = getattr(obj, related_manager_attr)
    geo_manager = getattr(obj, geo_manager_attr) if geo_manager_attr else related_manager
    countries, cities, states, regions = locations_from_related(
        geo_manager, location_attr=geo_location_attr
    )

    text = f"{obj.title or ''} {obj.description or ''}".strip()

    doc = {
        "record_status": obj.record_status,
        "cities": cities,
        "states": states,
        "regions": regions,
        "countries": countries,
        "thematic_level_0": level_0,
        "thematic_level_1": level_1,
        "thematic_level_2": level_2,
        "text": text,
        "title": obj.title,
        "directory_type": directory_type,
        "link": obj.link,
        "description": obj.description,
        "practice": as_label(obj.practice),
        "action": as_label(obj.action),
        "classification": obj.classification,
        "source": source_value,
        "institutional_contribution": obj.institutional_contribution,
        "universe": ["brazil"],
        "scope": [scope_label],
        "database": ["ocabr"],
        "pipeline": "oca",
        "graphs": ["thematic_level_0"],
        "type": "directory",
        "created": to_iso(obj.created),
        "updated": to_iso(obj.updated),
    }
    if related_names_field:
        doc[related_names_field] = [item.name for item in related_manager.all()]
    if include_disclaimer:
        doc["disclaimer"] = build_disclaimer(obj)
    return doc


def index_queryset_to_opensearch(
    *,
    objects,
    index_name,
    build_doc_fn,
    batch_size=200,
    refresh=False,
):
    client = get_opensearch_client()
    if not client:
        logger.warning("OpenSearch client nao configurado.")
        return

    queryset = objects
    total = queryset.count()
    if total == 0:
        logger.warning("Nenhum registro publicado para indexar.")
        return

    logger.info(f"Indexando {total} registros em {index_name}...")
    success_count = 0
    error_count = 0
    batch = []

    for obj in queryset.iterator(chunk_size=batch_size):
        try:
            doc = build_doc_fn(obj)
            batch.append({"_index": index_name, "_id": obj.id, "_source": doc})
        except Exception as exc:
            error_count += 1
            logger.exception(f"Falha ao serializar objeto {obj.id}: {exc}")

        if len(batch) >= batch_size:
            success, errors = bulk(client, batch, raise_on_error=False)
            success_count += success
            error_count += len(errors)
            batch = []

    if batch:
        success, errors = bulk(client, batch, raise_on_error=False)
        success_count += success
        error_count += len(errors)

    if refresh:
        client.indices.refresh(index=index_name)


def index_directory_instance(
    *,
    instance,
    index_name,
    build_doc_fn,
    refresh=True,
):
    client = get_opensearch_client()
    if not client:
        logger.warning("OpenSearch client nao configurado.")
        return

    if not index_name:
        logger.warning(f"Index name nao configurado para {instance.__class__.__name__}.")
        return

    try:
        doc = build_doc_fn(instance)
        client.index(index=index_name, id=instance.id, body=doc, refresh=refresh)
    except Exception as exc:
        logger.warning(
            f"Falha ao indexar {instance.__class__.__name__} {instance.id} em {index_name}: {exc}"
        )


def delete_directory_instance(*, instance_id, index_name, refresh=True):
    client = get_opensearch_client()
    if not client:
        logger.warning("OpenSearch client nao configurado.")
        return

    if not index_name:
        logger.warning("Index name nao configurado para remocao de documento.")
        return

    try:
        client.delete(index=index_name, id=instance_id, refresh=refresh)
    except Exception as exc:
        logger.warning(
            f"Falha ao remover documento {instance_id} de {index_name}: {exc}"
        )
