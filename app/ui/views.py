"""
Flask UI views (server-rendered pages).
"""
from flask import Blueprint, render_template

from app.database.db_manager import get_all_jobs, get_records, get_runs_for_job

ui_bp = Blueprint("ui", __name__)


@ui_bp.route("/")
def dashboard():
    jobs = get_all_jobs()
    total_records = get_records(limit=1_000_000)
    return render_template(
        "dashboard.html",
        jobs=jobs,
        total_jobs=len(jobs),
        total_records=len(total_records),
    )


@ui_bp.route("/jobs")
def jobs_page():
    jobs = get_all_jobs()
    return render_template("jobs.html", jobs=jobs)


@ui_bp.route("/jobs/<int:job_id>")
def job_detail(job_id):
    from app.database.db_manager import get_job
    job = get_job(job_id)
    if not job:
        return render_template("404.html"), 404
    runs = get_runs_for_job(job_id, limit=10)
    records = get_records(job_id=job_id, limit=50)
    return render_template("job_detail.html", job=job, runs=runs, records=records)


@ui_bp.route("/records")
def records_page():
    records = get_records(limit=200)
    return render_template("records.html", records=records)
