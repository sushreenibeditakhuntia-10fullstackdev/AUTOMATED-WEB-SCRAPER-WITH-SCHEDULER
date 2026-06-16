"""
Celery tasks: run_scraper_job and run_all_active_jobs.
"""
import json
from datetime import datetime, timezone

from app.scheduler.celery_app import celery_app
from app.utils.logger import get_logger

logger = get_logger(__name__)


@celery_app.task(bind=True, name="tasks.run_scraper_job", max_retries=2)
def run_scraper_job(self, job_id: int):
    """
    Execute a single scraper job identified by job_id.
    Persists run metadata and records to the database.
    """
    # Import here to avoid circular imports at module load time
    from app import create_app
    from app.database.db_manager import (
        create_run, finish_run, get_job, save_records, start_run,
    )
    from app.scrapers.requests_scraper import RequestsScraper
    from app.scrapers.selenium_scraper import SeleniumScraper

    flask_app = create_app()
    with flask_app.app_context():
        job = get_job(job_id)
        if not job:
            logger.error("Job id=%s not found", job_id)
            return {"status": "error", "message": f"Job {job_id} not found"}

        if not job.is_active:
            logger.info("Job id=%s is inactive — skipping", job_id)
            return {"status": "skipped"}

        run = create_run(job_id=job_id, celery_task_id=self.request.id)
        start_run(run.id)
        logger.info("Started run id=%s for job '%s'", run.id, job.name)

        scraper = None
        try:
            config = json.loads(job.config_json) if job.config_json else {}

            if job.scraper_type == "selenium":
                scraper = SeleniumScraper(config)
            else:
                scraper = RequestsScraper(config)

            records = scraper.scrape(job.url)
            count = save_records(run.id, job_id, records)
            finish_run(run.id, records_scraped=count)
            logger.info("Run id=%s finished: %d records saved", run.id, count)
            return {"status": "success", "run_id": run.id, "records": count}

        except Exception as exc:
            error_msg = str(exc)
            logger.exception("Run id=%s failed: %s", run.id, error_msg)
            finish_run(run.id, error=error_msg)
            raise self.retry(exc=exc, countdown=60)

        finally:
            if scraper:
                scraper.teardown()


@celery_app.task(name="tasks.run_all_active_jobs")
def run_all_active_jobs():
    """Dispatch run_scraper_job for every active job — called by the beat scheduler."""
    from app import create_app
    from app.database.db_manager import get_all_jobs

    flask_app = create_app()
    with flask_app.app_context():
        jobs = [j for j in get_all_jobs() if j.is_active]
        logger.info("Beat: dispatching %d active jobs", len(jobs))
        for job in jobs:
            run_scraper_job.delay(job.id)
        return {"dispatched": len(jobs)}
