import pytest

from app import create_app


@pytest.fixture
def app():
    """Provide a Flask app instance for tests."""
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
