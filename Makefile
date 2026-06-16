.PHONY: install run worker beat seed test lint clean

# ── Setup ────────────────────────────────────────────────────────────────────
install:
	pip install -r requirements.txt

# ── Run services ─────────────────────────────────────────────────────────────
run:
	python run.py

worker:
	celery -A app.scheduler.celery_app worker --loglevel=info --concurrency=2

beat:
	celery -A app.scheduler.celery_app beat --loglevel=info

# Both worker + beat in one terminal (dev only)
worker-beat:
	celery -A app.scheduler.celery_app worker --beat --loglevel=info --concurrency=2

# ── Database ──────────────────────────────────────────────────────────────────
seed:
	python seed.py

# ── Testing ───────────────────────────────────────────────────────────────────
test:
	pytest tests/ -v

test-cov:
	pytest tests/ -v --cov=app --cov-report=term-missing

# ── Code quality ──────────────────────────────────────────────────────────────
lint:
	flake8 app/ config/ tests/ --max-line-length=100 --ignore=E501,W503

# ── Cleanup ───────────────────────────────────────────────────────────────────
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete
	rm -rf .pytest_cache .coverage htmlcov
	rm -rf data/exports/*.csv logs/*.log
