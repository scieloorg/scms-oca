import logging

from harvest.exception_logs import ExceptionContext
from harvest.parse_info_oai_pmh import get_info_article


def harvest_records(
    recs,
    user,
    nodes,
    model,
    log_model,
    fk_field,
    label,
):
    for rec in recs:
        if not rec.header.identifier:
            continue
        logging.info(
            f"Colletando {label}: {rec.header.identifier}. datestamp: {rec.header.datestamp}"
        )
        harvested_obj, _ = model.objects.get_or_create(
            identifier=rec.header.identifier,
            creator=user,
        )
        harvested_obj.mark_as_in_progress()
        exc_context = ExceptionContext(
            harvest_object=harvested_obj,
            log_model=log_model,
            fk_field=fk_field,
        )
        article_info = get_info_article(rec, exc_context, nodes=nodes)
        harvested_obj.set_attrs_from_article_info(
            article_info=article_info,
            datestamp=rec.header.datestamp,
        )
        exc_context.save_to_db()
        exc_context.mark_status_harvest()
