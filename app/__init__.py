"""Flask application factory."""

import os

from dotenv import load_dotenv
from flask import Flask
from flask_login import LoginManager

from app.constants import (
    DEVELOPMENT,
    ENVIRONMENT,
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    GOOGLE_DISCOVERY_URL,
    PRODUCTION,
    SECRET_KEY,
    SM_FLASK_SECRET_KEY,
    SM_GOOGLE_CLIENT_ID,
    SM_GOOGLE_CLIENT_SECRET,
)
from app.utils.logging.logger import configure_logging, get_logger
from app.utils.secret_manager import get_secret

from .config import get_config

logger = get_logger(__name__)


def create_app() -> Flask:
    """
    Application factory for creating Flask app instance.

    Configuration is loaded based on the FLASK_ENV environment variable:
    - local: LocalConfig (local dev, DEBUG=True, loads .env file)
    - development: DevelopmentConfig (dev deployment to GCP, DEBUG=False)
    - production: ProductionConfig (prod deployment to GCP, DEBUG=False, strict validation)
    - testing: TestingConfig (unit tests)

    Returns:
        Flask: Configured Flask application instance
    """
    load_dotenv(override=False)

    app = Flask(__name__)

    # Load configuration
    _configure_app(app)

    # Configure logging (must be done after config is loaded)
    configure_logging(app)

    # Initialize extensions
    _init_login_manager(app)
    _init_oauth(app)

    # Register blueprints
    _register_blueprints(app)

    logger.info(
        f"Application initialized successfully in {app.config.get(ENVIRONMENT)} environment"
    )

    return app


def _configure_app(app: Flask) -> None:
    """Load configuration and setup secret key."""
    config_class = get_config()
    app.config.from_object(config_class)
    _setup_secret_keys(app)


def _setup_secret_keys(app: Flask) -> None:
    """
    Retrieve secrets from appropriate source based on environment.

    - PRODUCTION/DEVELOPMENT: Load from Secret Manager
    - Other environments: Load from environment variables

    Raises:
        ValueError: If any required secrets are missing
    """
    secret_mappings = {
        SECRET_KEY: SM_FLASK_SECRET_KEY,
        GOOGLE_CLIENT_ID: SM_GOOGLE_CLIENT_ID,
        GOOGLE_CLIENT_SECRET: SM_GOOGLE_CLIENT_SECRET,
    }

    environment = app.config.get(ENVIRONMENT)
    use_secret_manager = environment in [PRODUCTION, DEVELOPMENT]

    missing_secrets = []

    for config_key, secret_name in secret_mappings.items():
        if use_secret_manager:
            try:
                secret_value = get_secret(secret_name)
            except Exception as e:
                logger.error(
                    f"Failed to retrieve {secret_name} from Secret Manager: {e}"
                )
                secret_value = None
        else:
            secret_value = os.environ.get(config_key)

        if not secret_value:
            missing_secrets.append(
                secret_name if use_secret_manager else config_key
            )
        else:
            app.config[config_key] = secret_value

    if missing_secrets:
        source = (
            "Secret Manager" if use_secret_manager else "environment variables"
        )
        raise ValueError(
            f"Missing required secrets from {source}: {', '.join(missing_secrets)}"
        )

    source = (
        "Secret Manager" if use_secret_manager else "environment variables"
    )
    logger.info(f"Successfully loaded all secrets from {source}")


def _init_login_manager(app: Flask) -> None:
    """Initialize Flask-Login extension."""
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    @login_manager.user_loader
    def load_user(user_id: str):
        """Load user from session by user ID."""
        from app.models.user import User

        return User.get(user_id)


def _init_oauth(app: Flask) -> None:
    """Initialize OAuth extension and register Google provider."""
    from app.auth.routes import oauth

    oauth.init_app(app)

    # Validate OAuth configuration
    client_id = app.config.get(GOOGLE_CLIENT_ID)
    client_secret = app.config.get(GOOGLE_CLIENT_SECRET)

    if not client_id or not client_secret:
        logger.warning(
            "Google OAuth credentials not configured. "
            "Authentication will not work properly."
        )

    oauth.register(
        name="google",
        client_id=client_id,
        client_secret=client_secret,
        server_metadata_url=app.config.get(GOOGLE_DISCOVERY_URL),
        client_kwargs={"scope": "openid email profile"},
    )
    logger.info("OAuth initialized successfully")


def _register_blueprints(app: Flask) -> None:
    """Register all application blueprints."""
    from .auth.routes import auth_bp
    from .routes import main_bp

    blueprints = [main_bp, auth_bp]
    for blueprint in blueprints:
        app.register_blueprint(blueprint)
