"""
Database manager: helpers for CRUD operations and CSV export.
"""
import csv
import json
import os
from datetime import datetime, timezone
from typing import List, Optional

from app.database.models import ScrapedRecord, ScraperJob, ScraperRun, db
from app.utils.logger import get_logger

logger = get_logger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Jobs
# ──────────────────────────────────────────────────────────────────────────────

def create_job(name: str, url: str, scraper_type: str = "requests",
               schedule_cron: Optional[str] = None,
               config_json: Optional[str] = None) -> ScraperJob:
    job = ScraperJob(
        name=name,
        url=url,
        scraper_type=scraper_type,
        schedule_cron=schedule_cron,
        config_json=config_json,
    )
    db.session.add(job)
    db.session.commit()
    logger.info("Created job '%s' (id=%s)", name, job.id)
    return job


def get_all_jobs() -> List[ScraperJob]:
    return ScraperJob.query.order_by(ScraperJob.created_at.desc()).all()


def get_job(job_id: int) -> Optional[ScraperJob]:
    return ScraperJob.query.get(job_id)


def update_job(job_id: int, **kwargs) -> Optional[ScraperJob]:
    job = get_job(job_id)
    if not job:
        return None
    for key, value in kwargs.items():
        if hasattr(job, key):
            setattr(job, key, value)
    job.updated_at = datetime.now(timezone.utc)
    db.session.commit()
    return job


def delete_job(job_id: int) -> bool:
    job = get_job(job_id)
    if not job:
        return False
    db.session.delete(job)
    db.session.commit()
    logger.info("Deleted job id=%s", job_id)
    return True


# ──────────────────────────────────────────────────────────────────────────────
# Runs
# ──────────────────────────────────────────────────────────────────────────────

def create_run(job_id: int, celery_task_id: Optional[str] = None) -> ScraperRun:
    run = ScraperRun(
        job_id=job_id,
        status="pending",
        celery_task_id=celery_task_id,
    )
    db.session.add(run)
    db.session.commit()
    return run


def start_run(run_id: int) -> Optional[ScraperRun]:
    run = ScraperRun.query.get(run_id)
    if run:
        run.status = "running"
        run.started_at = datetime.now(timezone.utc)
        db.session.commit()
    return run


def finish_run(run_id: int, records_scraped: int = 0,
               error: Optional[str] = None) -> Optional[ScraperRun]:
    run = ScraperRun.query.get(run_id)
    if run:
        run.status = "failed" if error else "success"
        run.finished_at = datetime.now(timezone.utc)
        run.records_scraped = records_scraped
        run.error_message = error
        db.session.commit()
    return run


def get_runs_for_job(job_id: int, limit: int = 20) -> List[ScraperRun]:
    return (
        ScraperRun.query
        .filter_by(job_id=job_id)
        .order_by(ScraperRun.started_at.desc())
        .limit(limit)
        .all()
    )


# ──────────────────────────────────────────────────────────────────────────────
# Records
# ──────────────────────────────────────────────────────────────────────────────

def save_records(run_id: int, job_id: int, records: List[dict]) -> int:
    """Bulk-insert scraped records and return saved count."""
    count = 0
    for rec in records:
        record = ScrapedRecord(
            run_id=run_id,
            job_id=job_id,
            title=rec.get("title"),
            url=rec.get("url"),
            price=rec.get("price"),
            description=rec.get("description"),
            category=rec.get("category"),
            rating=rec.get("rating"),
            extra_data=json.dumps(rec.get("extra_data", {})),
        )
        db.session.add(record)
        count += 1
    db.session.commit()
    logger.info("Saved %d records for run_id=%s", count, run_id)
    return count


def get_records(job_id: Optional[int] = None,
                run_id: Optional[int] = None,
                limit: int = 500) -> List[ScrapedRecord]:
    query = ScrapedRecord.query
    if job_id:
        query = query.filter_by(job_id=job_id)
    if run_id:
        query = query.filter_by(run_id=run_id)
    return query.order_by(ScrapedRecord.scraped_at.desc()).limit(limit).all()


# ──────────────────────────────────────────────────────────────────────────────
# Export
# ──────────────────────────────────────────────────────────────────────────────

def export_to_csv(job_id: Optional[int] = None,
                  run_id: Optional[int] = None,
                  export_dir: str = "data/exports") -> str:
    """Export scraped records to a CSV file and return the file path."""
    os.makedirs(export_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix = f"job{job_id}" if job_id else f"run{run_id}" if run_id else "all"
    filename = f"scrape_{suffix}_{timestamp}.csv"
    filepath = os.path.join(export_dir, filename)

    records = get_records(job_id=job_id, run_id=run_id, limit=100_000)

    fieldnames = ["id", "job_id", "run_id", "title", "url", "price",
                  "description", "category", "rating", "extra_data", "scraped_at"]

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for rec in records:
            writer.writerow({k: getattr(rec, k, "") for k in fieldnames})

    logger.info("Exported %d records to %s", len(records), filepath)
    return filepath
