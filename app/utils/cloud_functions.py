"""
Utility functions for interacting with Google Cloud Functions.
"""

import os


def get_function_url(function_name: str, region: str = "europe-west1") -> str:
    """
    Generate the URL for a Google Cloud Function.

    Args:
        function_name: The name of the Cloud Function
        region: The GCP region where the function is deployed (default: europe-west1)

    Returns:
        The full HTTPS URL for the Cloud Function

    Raises:
        ValueError: If GOOGLE_CLOUD_PROJECT environment variable is not set
    """
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")

    if not project_id:
        raise ValueError(
            "GOOGLE_CLOUD_PROJECT environment variable is not set"
        )

    return f"https://{region}-{project_id}.cloudfunctions.net/{function_name}"
