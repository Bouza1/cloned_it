import os

from google.cloud import secretmanager

from app.constants import PROJECT_ID


def get_secret(secret: str) -> str:
    """
    Fetch the latest version of a secret from Secret Manager
    secret_name: str = name of the secret to fetch
    Returns:
        str: The secret value
    """
    secret_name = f"projects/{os.environ.get(PROJECT_ID)}/secrets/{secret}/versions/latest"
    client = secretmanager.SecretManagerServiceClient()
    response = client.access_secret_version(request={"name": secret_name})
    return response.payload.data.decode("UTF-8")
