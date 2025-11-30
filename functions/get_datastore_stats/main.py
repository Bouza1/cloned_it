"""Cloud Function to get Datastore statistics.
"""

import functions_framework
from shared import datastore_client


@functions_framework.http
def get_datastore_stats(request):
    """
    HTTP Cloud Function to get Datastore statistics.

    Args:
        request (flask.Request): HTTP request object.

    Returns:
        JSON response with Datastore statistics
    """
    try:
        client = datastore_client.get_datastore_client()

        user_kinds = datastore_client.get_all_kinds(include_system_kinds=False)

        kind_counts = datastore_client.get_kind_stats()
        total_entities = sum(kind_counts.values())

        response = {
            "status": "success",
            "project": client.project,
            "database": "default",
            "total_entities": total_entities,
            "kinds": user_kinds,
            "kind_counts": kind_counts,
        }

        return response, 200

    except Exception as e:
        error_response = {
            "status": "error",
            "message": str(e),
            "error_type": type(e).__name__,
        }
        return error_response, 500

