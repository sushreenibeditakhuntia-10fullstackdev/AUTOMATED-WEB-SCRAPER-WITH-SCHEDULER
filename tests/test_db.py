"""
Tests for database manager functions.
"""
import json

import pytest


class TestJobManager:
    def test_create_and_get_job(self, db, app):
        from app.database.db_manager import create_job, get_job
        with app.app_context():
            job = create_job("DB Test", "https://example.com")
            fetched = get_job(job.id)
            assert fetched is not None
            assert fetched.name == "DB Test"

    def test_update_job(self, db, app, sample_job):
        from app.database.db_manager import update_job, get_job
        with app.app_context():
            update_job(sample_job.id, name="Updated Name", is_active=False)
            job = get_job(sample_job.id)
            assert job.name == "Updated Name"
            assert job.is_active is False

    def test_delete_job(self, db, app):
        from app.database.db_manager import create_job, delete_job, get_job
        with app.app_context():
            job = create_job("Delete Me", "https://x.com")
            jid = job.id
            assert delete_job(jid) is True
            assert get_job(jid) is None

    def test_delete_nonexistent_job(self, db, app):
        from app.database.db_manager import delete_job
        with app.app_context():
            assert delete_job(999999) is False


class TestRunManager:
    def test_create_start_finish_run(self, db, app, sample_job):
        from app.database.db_manager import create_run, start_run, finish_run
        with app.app_context():
            run = create_run(sample_job.id)
            assert run.status == "pending"
            start_run(run.id)
            # Re-query
            from app.database.models import ScraperRun
            r = ScraperRun.query.get(run.id)
            assert r.status == "running"
            finish_run(run.id, records_scraped=10)
            r = ScraperRun.query.get(run.id)
            assert r.status == "success"
            assert r.records_scraped == 10

    def test_finish_run_with_error(self, db, app, sample_job):
        from app.database.db_manager import create_run, finish_run
        from app.database.models import ScraperRun
        with app.app_context():
            run = create_run(sample_job.id)
            finish_run(run.id, error="Something went wrong")
            r = ScraperRun.query.get(run.id)
            assert r.status == "failed"
            assert "Something went wrong" in r.error_message


class TestRecordManager:
    def test_save_and_get_records(self, db, app, sample_job):
        from app.database.db_manager import create_run, save_records, get_records
        with app.app_context():
            run = create_run(sample_job.id)
            records = [
                {"title": "Book A", "price": "£5.99", "url": "https://x.com/a"},
                {"title": "Book B", "price": "£9.99", "url": "https://x.com/b"},
            ]
            count = save_records(run.id, sample_job.id, records)
            assert count == 2
            saved = get_records(job_id=sample_job.id)
            assert len(saved) >= 2

    def test_export_to_csv(self, db, app, sample_job, tmp_path):
        from app.database.db_manager import create_run, save_records, export_to_csv
        with app.app_context():
            run = create_run(sample_job.id)
            save_records(run.id, sample_job.id, [{"title": "T", "price": "£1"}])
            path = export_to_csv(job_id=sample_job.id, export_dir=str(tmp_path))
            import os, csv
            assert os.path.exists(path)
            with open(path) as f:
                rows = list(csv.DictReader(f))
            assert len(rows) >= 1
