"""
Seed script: populates the database with sample scraper jobs.

Usage:
    python seed.py
"""
import json
import os
import sys

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from app.database.db_manager import create_job, get_all_jobs
from app.utils.logger import get_logger

logger = get_logger("seed")
SAMPLE_FILE = os.path.join("config", "sample_targets.json")


def seed():
    flask_app = create_app()
    with flask_app.app_context():
        existing = {j.name for j in get_all_jobs()}

        with open(SAMPLE_FILE, encoding="utf-8") as f:
            targets = json.load(f)

        created = 0
        for t in targets:
            if t["name"] in existing:
                logger.info("Skipping existing job: %s", t["name"])
                continue
            config_raw = t.get("config_json")
            config_str = json.dumps(config_raw) if isinstance(config_raw, dict) else config_raw
            create_job(
                name=t["name"],
                url=t["url"],
                scraper_type=t.get("scraper_type", "requests"),
                schedule_cron=t.get("schedule_cron"),
                config_json=config_str,
            )
            logger.info("Created job: %s", t["name"])
            created += 1

        logger.info("Seed complete — %d new job(s) created.", created)


if __name__ == "__main__":
    seed()
