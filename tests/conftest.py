"""
Pytest fixtures shared across all test modules.
"""
import json
import pytest

from app import create_app
from app.database.models import db as _db
from config.settings import TestingConfig


@pytest.fixture(scope="session")
def app():
    """Create application with in-memory SQLite for the test session."""
    flask_app = create_app(TestingConfig)
    with flask_app.app_context():
        _db.create_all()
        yield flask_app
        _db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def db(app):
    """Return a clean database session for each test."""
    with app.app_context():
        yield _db
        _db.session.rollback()


@pytest.fixture()
def sample_job(db):
    """Insert a sample scraper job and return it."""
    from app.database.db_manager import create_job
    job = create_job(
        name="Test Job",
        url="https://books.toscrape.com/",
        scraper_type="requests",
        config_json=json.dumps({
            "list_selector": "article.product_pod",
            "selectors": {"title": "h3 > a", "price": "p.price_color"},
        }),
    )
    return job
