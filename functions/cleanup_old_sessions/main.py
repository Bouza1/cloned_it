"""Cloud Function to cleanup old user sessions from Datastore.

This function is triggered by Pub/Sub and it removes sessions older than 7 days to keep the datstore clean.
"""

import functions_framework
from datetime import datetime, timedelta
from google.cloud import datastore


@functions_framework.cloud_event
def cleanup_old_sessions(cloud_event):
    """
    Cloud Function triggered by Pub/Sub to cleanup old sessions.

    Args:
        cloud_event: Cloud Event containing the Pub/Sub message
    """
    try:

        db = datastore.Client()

        # Calculate cutoff date
        cutoff_date = datetime.now() - timedelta(days=7)

        # Query for old sessions
        # Assuming sessions have a 'last_active' or 'created_at' timestamp field
        query = db.query(kind="Session")
        query.add_filter("last_active", "<", cutoff_date)

        old_sessions = list(query.fetch())

        # Delete old sessions in batch
        deleted_count = 0
        batch = []
        batch_size = 500  # Datastore batch limit

        for session in old_sessions:
            batch.append(session.key)

            # Process batch when it reaches the limit
            if len(batch) >= batch_size:
                db.delete_multi(batch)
                deleted_count += len(batch)
                batch = []

        # Delete remaining sessions
        if batch:
            db.delete_multi(batch)
            deleted_count += len(batch)

        print(f"Successfully deleted {deleted_count} old sessions")

        return {
            "status": "success",
            "deleted_count": deleted_count,
            "cutoff_date": cutoff_date.isoformat(),
        }

    except Exception as e:
        print(f"Error cleaning up sessions: {e}")
        return {
            "status": "error",
            "message": str(e),
            "error_type": type(e).__name__,
        }

