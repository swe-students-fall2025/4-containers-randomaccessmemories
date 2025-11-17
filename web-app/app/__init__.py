from flask import Flask
from flask_cors import CORS
from .config import Config

def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)
    app.config["MAX_CONTENT_LENGTH"] = Config.MAX_FILE_MB * 1024 * 1024
    CORS(app)

    # Register routes
    from .routes import bp as routes_bp
    app.register_blueprint(routes_bp)

    return app

