"""
Flask REST API routes for managing jobs, runs, records, and exports.
"""
import os

from flask import Blueprint, jsonify, request, send_file

from app.database.db_manager import (
    create_job,
    delete_job,
    export_to_csv,
    get_all_jobs,
    get_job,
    get_records,
    get_runs_for_job,
    update_job,
)
from app.utils.logger import get_logger
from config.settings import active_config

logger = get_logger(__name__)

api_bp = Blueprint("api", __name__, url_prefix="/api")


# ── helpers ───────────────────────────────────────────────────────────────────

def _ok(data, status=200):
    return jsonify({"success": True, "data": data}), status


def _err(message, status=400):
    return jsonify({"success": False, "error": message}), status


# ── jobs ──────────────────────────────────────────────────────────────────────

@api_bp.route("/jobs", methods=["GET"])
def list_jobs():
    jobs = get_all_jobs()
    return _ok([j.to_dict() for j in jobs])


@api_bp.route("/jobs/<int:job_id>", methods=["GET"])
def get_job_detail(job_id):
    job = get_job(job_id)
    if not job:
        return _err(f"Job {job_id} not found", 404)
    return _ok(job.to_dict())


@api_bp.route("/jobs", methods=["POST"])
def create_job_route():
    body = request.get_json(silent=True) or {}
    name = body.get("name", "").strip()
    url = body.get("url", "").strip()
    if not name or not url:
        return _err("'name' and 'url' are required")
    job = create_job(
        name=name,
        url=url,
        scraper_type=body.get("scraper_type", "requests"),
        schedule_cron=body.get("schedule_cron"),
        config_json=body.get("config_json"),
    )
    return _ok(job.to_dict(), 201)


@api_bp.route("/jobs/<int:job_id>", methods=["PUT"])
def update_job_route(job_id):
    body = request.get_json(silent=True) or {}
    job = update_job(job_id, **body)
    if not job:
        return _err(f"Job {job_id} not found", 404)
    return _ok(job.to_dict())


@api_bp.route("/jobs/<int:job_id>", methods=["DELETE"])
def delete_job_route(job_id):
    if not delete_job(job_id):
        return _err(f"Job {job_id} not found", 404)
    return _ok({"deleted": job_id})


# ── run trigger ───────────────────────────────────────────────────────────────

@api_bp.route("/jobs/<int:job_id>/run", methods=["POST"])
def trigger_run(job_id):
    job = get_job(job_id)
    if not job:
        return _err(f"Job {job_id} not found", 404)
    try:
        from app.scheduler.tasks import run_scraper_job
        task = run_scraper_job.delay(job_id)
        return _ok({"task_id": task.id, "job_id": job_id}, 202)
    except Exception as exc:
        logger.error("Failed to enqueue job %s: %s", job_id, exc)
        return _err(f"Could not enqueue job: {exc}", 500)


# ── runs ──────────────────────────────────────────────────────────────────────

@api_bp.route("/jobs/<int:job_id>/runs", methods=["GET"])
def list_runs(job_id):
    runs = get_runs_for_job(job_id)
    return _ok([r.to_dict() for r in runs])


# ── records ───────────────────────────────────────────────────────────────────

@api_bp.route("/records", methods=["GET"])
def list_records():
    job_id = request.args.get("job_id", type=int)
    run_id = request.args.get("run_id", type=int)
    limit = request.args.get("limit", 100, type=int)
    records = get_records(job_id=job_id, run_id=run_id, limit=limit)
    return _ok([r.to_dict() for r in records])


# ── export ────────────────────────────────────────────────────────────────────

@api_bp.route("/export", methods=["GET"])
def export():
    job_id = request.args.get("job_id", type=int)
    run_id = request.args.get("run_id", type=int)
    try:
        filepath = export_to_csv(
            job_id=job_id,
            run_id=run_id,
            export_dir=active_config.EXPORT_DIR,
        )
        return send_file(
            os.path.abspath(filepath),
            mimetype="text/csv",
            as_attachment=True,
            download_name=os.path.basename(filepath),
        )
    except Exception as exc:
        logger.error("Export failed: %s", exc)
        return _err(f"Export failed: {exc}", 500)


# ── health ────────────────────────────────────────────────────────────────────

@api_bp.route("/health", methods=["GET"])
def health():
    return _ok({"status": "ok"})
