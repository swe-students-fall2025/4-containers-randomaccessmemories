"""Flask application factory."""

from flask import Flask
from flask_cors import CORS
from .config import Config


def create_app() -> Flask:
    """Create and configure Flask application."""
    app = Flask(__name__)
    app.config.from_object(Config)
    app.config["MAX_CONTENT_LENGTH"] = Config.MAX_FILE_MB * 1024 * 1024
    CORS(app)

    # Register routes - import moved inside function to avoid circular imports
    from .routes import bp as routes_bp  # pylint: disable=import-outside-toplevel

    app.register_blueprint(routes_bp)

    return app
