from django.contrib.auth import get_user_model
from django.utils.translation import gettext as _

from config import celery_app

from indicator import directory, sciprod


User = get_user_model()


@celery_app.task(bind=True, name=_("Geração de indicadores de ações"))
def task_generate_directory_indicators(
    self, creator_id, action_name=None, filter_by=None, group_by=None, min_items=None,
):
    creator = User.objects.get(id=creator_id) or User.objects.first()
    action__names = [action_name]

    group_by = group_by or {}

    directory.generate_indicators(creator, action__names, filter_by, group_by, min_items)


@celery_app.task(bind=True, name=_("Geração de indicadores de artigos científicos"))
def task_generate_sciprod_indicators(
    self, creator_id, filter_by=None, group_by=None, begin_year=None, end_year=None, min_items=None,
):
    creator = User.objects.get(id=creator_id) or User.objects.first()

    group_by = group_by or {}

    sciprod.generate_indicators(creator, filter_by, group_by, begin_year, end_year, min_items)
