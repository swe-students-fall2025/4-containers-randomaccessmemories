"""Flask application factory."""

from flask import Flask


def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)

    # Load config
    from .config import Config  # pylint: disable=import-outside-toplevel

    app.config.from_object(Config)

    # Secret key for sessions
    app.secret_key = Config.SECRET_KEY

    # Register blueprints
    from . import routes  # pylint: disable=import-outside-toplevel

    app.register_blueprint(routes.bp)

    return app
