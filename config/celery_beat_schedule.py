"""
Celery Beat periodic task schedule.

Start the beat scheduler with:
    celery -A app.scheduler.celery_app beat --loglevel=info

The `run_all_active_jobs` task fires every 15 minutes and dispatches
individual `run_scraper_job` tasks for each active job that has a
matching cron schedule (schedule_cron is checked inside the task).
"""
from celery.schedules import crontab

CELERYBEAT_SCHEDULE = {
    # Poll active jobs every 15 minutes
    "run-all-active-jobs-every-15min": {
        "task": "tasks.run_all_active_jobs",
        "schedule": crontab(minute="*/15"),
    },
}

CELERY_TIMEZONE = "UTC"
