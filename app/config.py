"""Configuration classes for different environments."""

import os
from typing import Optional

from app.constants import (
    DEVELOPMENT,
    FLASK_ENV,
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    LOCAL,
    PRODUCTION,
    SECRET_KEY,
    TESTING,
)


class Config:
    """Base configuration class with common settings."""

    # Flask settings
    SECRET_KEY: Optional[str] = os.environ.get(
        SECRET_KEY, "dev-secret-key-change-in-production"
    )
    TESTING = False
    DEBUG = False

    # App settings
    ENVIRONMENT = os.environ.get(FLASK_ENV, LOCAL)

    # Google OAuth settings
    GOOGLE_CLIENT_ID: Optional[str] = os.environ.get(GOOGLE_CLIENT_ID)
    GOOGLE_CLIENT_SECRET: Optional[str] = os.environ.get(GOOGLE_CLIENT_SECRET)
    GOOGLE_DISCOVERY_URL = (
        "https://accounts.google.com/.well-known/openid-configuration"
    )

    # Session settings
    SESSION_COOKIE_SECURE = True  # Only send cookies over HTTPS
    SESSION_COOKIE_HTTPONLY = (
        True  # Prevent JavaScript access to session cookie
    )
    SESSION_COOKIE_SAMESITE = "Lax"  # CSRF protection
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hour session timeout


class LocalConfig(Config):
    """Local development configuration."""

    DEBUG = True
    TESTING = False
    ENVIRONMENT = LOCAL

    # Allow insecure cookies for local development (HTTP)
    SESSION_COOKIE_SECURE = False


class DevelopmentConfig(Config):
    """Development environment configuration."""

    DEBUG = False
    TESTING = False
    ENVIRONMENT = DEVELOPMENT


class ProductionConfig(Config):
    """Production environment configuration."""

    DEBUG = False
    TESTING = False
    ENVIRONMENT = PRODUCTION


class TestingConfig(Config):
    """Testing environment configuration."""

    DEBUG = True
    TESTING = True
    ENVIRONMENT = TESTING
    SECRET_KEY = "test-secret-key"


# Configuration mapping
config = {
    LOCAL: LocalConfig,  # Local development
    DEVELOPMENT: DevelopmentConfig,  # Dev deployment (GCP dev project)
    PRODUCTION: ProductionConfig,  # Prod deployment (GCP prod project)
    TESTING: TestingConfig,  # Unit tests
}


def get_config() -> type[Config]:
    """
    Get the appropriate configuration class based on FLASK_ENV.

    Defaults to LocalConfig if FLASK_ENV is not set or invalid.
    """
    env = os.environ.get(FLASK_ENV, LOCAL).lower()
    return config.get(env, LocalConfig)
