"""
SQLAlchemy database models for the web scraper.
"""
from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class ScraperJob(db.Model):
    """Represents a configured scraping job / target website."""

    __tablename__ = "scraper_jobs"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    url = db.Column(db.String(2000), nullable=False)
    scraper_type = db.Column(db.String(50), default="requests")  # requests | selenium
    schedule_cron = db.Column(db.String(100), nullable=True)      # cron expression
    is_active = db.Column(db.Boolean, default=True)
    config_json = db.Column(db.Text, nullable=True)               # JSON selector config
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    runs = db.relationship("ScraperRun", back_populates="job", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "url": self.url,
            "scraper_type": self.scraper_type,
            "schedule_cron": self.schedule_cron,
            "is_active": self.is_active,
            "config_json": self.config_json,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ScraperRun(db.Model):
    """Represents a single execution of a scraper job."""

    __tablename__ = "scraper_runs"

    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey("scraper_jobs.id"), nullable=False)
    status = db.Column(db.String(50), default="pending")  # pending|running|success|failed
    started_at = db.Column(db.DateTime, nullable=True)
    finished_at = db.Column(db.DateTime, nullable=True)
    records_scraped = db.Column(db.Integer, default=0)
    error_message = db.Column(db.Text, nullable=True)
    celery_task_id = db.Column(db.String(200), nullable=True)

    job = db.relationship("ScraperJob", back_populates="runs")
    records = db.relationship("ScrapedRecord", back_populates="run", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "job_id": self.job_id,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "records_scraped": self.records_scraped,
            "error_message": self.error_message,
            "celery_task_id": self.celery_task_id,
        }


class ScrapedRecord(db.Model):
    """A single scraped data record."""

    __tablename__ = "scraped_records"

    id = db.Column(db.Integer, primary_key=True)
    run_id = db.Column(db.Integer, db.ForeignKey("scraper_runs.id"), nullable=False)
    job_id = db.Column(db.Integer, db.ForeignKey("scraper_jobs.id"), nullable=False)
    title = db.Column(db.String(1000), nullable=True)
    url = db.Column(db.String(2000), nullable=True)
    price = db.Column(db.String(100), nullable=True)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(200), nullable=True)
    rating = db.Column(db.String(50), nullable=True)
    extra_data = db.Column(db.Text, nullable=True)   # JSON for flexible fields
    scraped_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    run = db.relationship("ScraperRun", back_populates="records")

    def to_dict(self):
        return {
            "id": self.id,
            "run_id": self.run_id,
            "job_id": self.job_id,
            "title": self.title,
            "url": self.url,
            "price": self.price,
            "description": self.description,
            "category": self.category,
            "rating": self.rating,
            "extra_data": self.extra_data,
            "scraped_at": self.scraped_at.isoformat() if self.scraped_at else None,
        }
