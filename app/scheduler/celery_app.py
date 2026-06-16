"""
Celery application factory and periodic task beat schedule.
"""
import json
from celery import Celery
from celery.schedules import crontab

from config.settings import active_config


def make_celery(flask_app=None) -> Celery:
    """Create and configure the Celery instance."""
    celery = Celery(
        "web_scraper",
        broker=active_config.CELERY_BROKER_URL,
        backend=active_config.CELERY_RESULT_BACKEND,
        include=["app.scheduler.tasks"],
    )

    celery.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        task_acks_late=True,
        worker_prefetch_multiplier=1,
        result_expires=3600,
    )

    if flask_app:
        class ContextTask(celery.Task):
            def __call__(self, *args, **kwargs):
                with flask_app.app_context():
                    return self.run(*args, **kwargs)

        celery.Task = ContextTask

    return celery


# Standalone instance used when running `celery -A app.scheduler.celery_app worker`
celery_app = make_celery()
