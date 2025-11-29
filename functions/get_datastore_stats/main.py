"""Cloud Function to get Datastore statistics.
"""

import functions_framework
from google.cloud import datastore


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
        # Initialize Datastore client
        db = datastore.Client()

        # Get all kinds
        query = db.query(kind="__kind__")
        query.keys_only()

        all_kinds = [entity.key.id_or_name for entity in query.fetch()]

        # Filter out system kinds (those starting with __)
        user_kinds = [k for k in all_kinds if not k.startswith("__")]

        # Count entities in each kind
        kind_counts = {}
        total_entities = 0

        for kind_name in user_kinds:
            query = db.query(kind=kind_name)
            query.keys_only() 
            count = len(list(query.fetch()))
            kind_counts[kind_name] = count
            total_entities += count

        # Build response
        response = {
            "status": "success",
            "project": db.project,
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

