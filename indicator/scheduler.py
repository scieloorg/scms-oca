from datetime import datetime
import logging
import json

from django.utils.translation import gettext as _
from django_celery_beat.models import PeriodicTask, CrontabSchedule

from indicator import exceptions


def get_or_create_periodic_task(
    name,
    task,
    kwargs,
    day_of_week=None,
    hour=None,
    minute=None,
    priority=None,
    enabled=True,
    only_once=False,
):
    try:
        periodic_task = PeriodicTask.objects.get(name=name)
    except PeriodicTask.MultipleObjectsReturned:
        periodic_task = PeriodicTask.objects.filter(name=name).delete()
    except PeriodicTask.DoesNotExist:
        pass

    try:
        periodic_task = PeriodicTask.objects.get(name=name)
    except PeriodicTask.DoesNotExist:
        periodic_task = PeriodicTask()
        periodic_task.name = name
        periodic_task.task = task
        periodic_task.kwargs = json.dumps(kwargs)

    periodic_task.priority = priority
    periodic_task.enabled = enabled
    periodic_task.one_off = only_once

    if not hour and not minute:
        hour, minute = sum_hours_and_minutes(hours_after_now=0, minutes_after_now=1)

    periodic_task.crontab = get_or_create_crontab_schedule(
        day_of_week=day_of_week,
        hour=hour,
        minute=minute,
    )
    periodic_task.save()
    logging.info(
        _("Agendado %s %s às %s:%s prioridade: %s")
        % (name, day_of_week, hour, str(minute).zfill(2), priority)
    )


def sum_hours_and_minutes(hours_after_now, minutes_after_now, now=None):
    """
    Retorna a soma dos minutos / horas a partir da hora atual
    """
    now = now or datetime.utcnow()
    hours = now.hour + hours_after_now
    minutes = now.minute + minutes_after_now
    if minutes > 59:
        hours += 1
    hours = hours % 24
    minutes = minutes % 60
    return hours, minutes


def get_or_create_crontab_schedule(day_of_week=None, hour=None, minute=None):
    try:
        crontab_schedule, status = CrontabSchedule.objects.get_or_create(
            day_of_week=day_of_week or "*",
            hour=hour or "*",
            minute=minute or "*",
        )
    except Exception as e:
        raise exceptions.GetOrCreateCrontabScheduleError(
            _("Unable to get_or_create_crontab_schedule {} {} {} {} {}").format(
                day_of_week, hour, minute, type(e), e
            )
        )
    return crontab_schedule
