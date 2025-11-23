import os

from google.cloud import secretmanager

from app.constants import PROJECT_ID
from app.utils.logging.logger import get_logger

logger = get_logger(__name__)


def get_secret(secret: str) -> str:
    """
    Fetch the latest version of a secret from Secret Manager.

    Args:
        secret: Name of the secret to fetch

    Returns:
        str: The secret value

    Raises:
        Exception: If secret retrieval fails
    """
    project_id = os.environ.get(PROJECT_ID)
    secret_name = f"projects/{project_id}/secrets/{secret}/versions/latest"

    try:
        client = secretmanager.SecretManagerServiceClient()
        response = client.access_secret_version(request={"name": secret_name})

        logger.info(
            f"Successfully retrieved secret from Secret Manager",
            extra={"secret_name": secret},
        )

        return response.payload.data.decode("UTF-8")
    except Exception as e:
        logger.error(
            f"Failed to retrieve secret from Secret Manager: {str(e)}",
            exc_info=True,
            extra={"secret_name": secret, "project_id": project_id},
        )
        raise
