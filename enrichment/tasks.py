from config import celery_app
from enrichment.process import run_world_regions_upload


@celery_app.task(name="Apply world regions upload")
def apply_world_regions_upload(upload_id):
    return run_world_regions_upload(upload_id)
