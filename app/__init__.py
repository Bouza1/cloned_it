import os

from dotenv import load_dotenv
from flask import Flask

from app.constants import FLASK_SECRET_KEY, SECRET_KEY
from app.utils.secret_manager import get_secret

from .config import get_config


def create_app() -> Flask:
    """
    Application factory for creating Flask app instance.

    Configuration is loaded based on the FLASK_ENV environment variable:
    - local: LocalConfig (local dev, DEBUG=True, loads .env file)
    - development: DevelopmentConfig (dev deployment to GCP, DEBUG=False)
    - production: ProductionConfig (prod deployment to GCP, DEBUG=False, strict validation)
    - testing: TestingConfig (unit tests)
    """

    load_dotenv(override=False)

    app = Flask(__name__)

    # Load configuration based on FLASK_ENV
    config_class = get_config()
    app.config.from_object(config_class)

    # Get secret_key from Secret Manager and set it to the app config
    app.config[SECRET_KEY] = get_secret(FLASK_SECRET_KEY)

    # Register blueprints
    from .routes import main_bp

    app.register_blueprint(main_bp)

    return app
