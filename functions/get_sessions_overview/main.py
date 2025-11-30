"""Cloud Function to get sessions overview.
"""

from shared.constants import  DATASTORE_KIND_SESSION, ERROR, ERROR_TYPE,  LAST_ACTIVE,  MESSAGE, STATUS, SUCCESS
import functions_framework
from datetime import datetime
from collections import defaultdict
from shared import datastore_client
from constants import ACTIVE_USERS_COUNT, EXPIRES_AT, LAST_ACTIVE_BREAKDOWN, TIMESTAMP, TOTAL_SESSIONS, USER_ID

@functions_framework.http
def get_sessions_overview(request):
    """
    HTTP Cloud Function to get sessions overview.

    Args:
        request (flask.Request): HTTP request object.

    Returns:
        JSON response with active users count and last_active breakdown by hour
    """
    try:
        db = datastore_client.get_datastore_client()
        
        # Query all sessions
        query = db.query(kind=DATASTORE_KIND_SESSION)
        sessions = list(query.fetch())
        
        # Count active users
        now = datetime.now()
        active_users = set()
        last_active_by_hour = defaultdict(int)
        
        for session in sessions:
            # Check if session is not expired
            expires_at = session.get(EXPIRES_AT)
            if expires_at and expires_at > now:
                user_id = session.get(USER_ID)
                if user_id:
                    active_users.add(user_id)
                
            # Categorize by last_active hour
            last_active = session.get(LAST_ACTIVE)
            if last_active:
                # Calculate how many hours ago
                hours_ago = int((now - last_active).total_seconds() / 3600)
                
                # Group into time buckets
                if hours_ago < 1:
                    last_active_by_hour["< 1 hour"] += 1
                elif hours_ago < 24:
                    last_active_by_hour[f"{hours_ago}-{hours_ago+1} hours"] += 1
                elif hours_ago < 168:  # 7 days
                    days_ago = hours_ago // 24
                    last_active_by_hour[f"{days_ago}-{days_ago+1} days"] += 1
                else:
                    last_active_by_hour["> 7 days"] += 1
        
        sorted_breakdown = dict(sorted(last_active_by_hour.items()))
        
        response = {
            STATUS: SUCCESS,
            ACTIVE_USERS_COUNT: len(active_users),
            TOTAL_SESSIONS: len(sessions),
            LAST_ACTIVE_BREAKDOWN: sorted_breakdown,
            TIMESTAMP: now.isoformat(),
        }

        return response, 200

    except Exception as e:
        error_response = {
            STATUS: ERROR,
            MESSAGE: str(e),
            ERROR_TYPE: type(e).__name__,
        }
        return error_response, 500

