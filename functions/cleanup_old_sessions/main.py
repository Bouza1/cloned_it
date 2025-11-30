"""Cloud Function to cleanup old user sessions from Datastore.

This function is triggered by Pub/Sub and it removes sessions older than 7 days to keep the datastore clean.
"""

from constants import DELETED_COUNT, CUTOFF_DATE
from shared.constants import DATASTORE_KIND_SESSION, ERROR, ERROR_TYPE, LAST_ACTIVE, MESSAGE, STATUS, SUCCESS
import functions_framework
from datetime import datetime, timedelta
from shared import datastore_client


@functions_framework.cloud_event
def cleanup_old_sessions(cloud_event):
    """
    Cloud Function triggered by Pub/Sub to cleanup old sessions.

    Args:
        cloud_event: Cloud Event containing the Pub/Sub message
    """
    try:
        db = datastore_client.get_datastore_client()

        # Calculate cutoff date
        cutoff_date = datetime.now() - timedelta(days=7)

        # Query for old sessions
        query = db.query(kind=DATASTORE_KIND_SESSION)
        query.add_filter(LAST_ACTIVE, "<", cutoff_date)

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
            STATUS: SUCCESS,
            DELETED_COUNT: deleted_count,
            CUTOFF_DATE: cutoff_date.isoformat(),
        }

    except Exception as e:
        print(f"Error cleaning up sessions: {e}")
        return {
            STATUS: ERROR,
            MESSAGE: str(e),
            ERROR_TYPE: type(e).__name__,
        }

