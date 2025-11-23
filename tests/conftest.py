import os

import pytest

from app import create_app


@pytest.fixture
def app():
    """Provide a Flask app instance for tests."""
    # Set testing environment before creating the app
    os.environ["FLASK_ENV"] = "testing"
    os.environ["GOOGLE_CLIENT_ID"] = "test-google-client-id"
    os.environ["GOOGLE_CLIENT_SECRET"] = "test-google-client-secret"

    test_app = create_app()
    test_app.config.update(
        {
            "TESTING": True,
        }
    )
    yield test_app


@pytest.fixture
def client(app):
    """Test client for making requests."""
    return app.test_client()
