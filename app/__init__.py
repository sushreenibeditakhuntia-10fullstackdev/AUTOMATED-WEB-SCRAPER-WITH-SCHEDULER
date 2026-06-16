"""
Flask application factory.
"""
import os

from flask import Flask
from flask_cors import CORS

from app.api.routes import api_bp
from app.database.models import db
from config.settings import active_config


def create_app(config=None) -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    app.config.from_object(config or active_config)

    CORS(app)

    # Ensure directories exist
    for directory in ["logs", "data/exports", "data/screenshots"]:
        os.makedirs(directory, exist_ok=True)

    # Init database
    db.init_app(app)
    with app.app_context():
        db.create_all()

    # Register blueprints
    app.register_blueprint(api_bp)

    # Register UI blueprint
    from app.ui.views import ui_bp
    app.register_blueprint(ui_bp)

    return app
