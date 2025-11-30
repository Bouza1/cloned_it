"""Cloud Function to get sessions overview.
"""

from shared.constants import  DATASTORE_KIND_SESSION, ERROR, ERROR_TYPE,  LAST_ACTIVE,  MESSAGE, STATUS, SUCCESS
import functions_framework
from datetime import datetime, timezone
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
        print("Starting get_sessions_overview function")
        db = datastore_client.get_datastore_client()
        
        # Query all sessions
        query = db.query(kind=DATASTORE_KIND_SESSION)
        sessions = list(query.fetch())
        print(f"Fetched {len(sessions)} total sessions from Datastore")
        
        # Count active users (use timezone-aware datetime to compare with Datastore timestamps)
        now = datetime.now(timezone.utc)
        print(f"Current UTC time: {now.isoformat()} (timezone-aware: {now.tzinfo is not None})")
        
        active_users = set()
        last_active_by_hour = defaultdict(int)
        expired_count = 0
        missing_expires_at = 0
        missing_last_active = 0
        
        for idx, session in enumerate(sessions):
            # Debug first session to verify data structure
            if idx == 0:
                print(f"Sample session keys: {list(session.keys())}")
                expires_at_sample = session.get(EXPIRES_AT)
                if expires_at_sample:
                    print(f"Sample expires_at type: {type(expires_at_sample).__name__}, "
                          f"timezone-aware: {getattr(expires_at_sample, 'tzinfo', None) is not None}, "
                          f"value: {expires_at_sample}")
                last_active_sample = session.get(LAST_ACTIVE)
                if last_active_sample:
                    print(f"Sample last_active type: {type(last_active_sample).__name__}, "
                          f"timezone-aware: {getattr(last_active_sample, 'tzinfo', None) is not None}, "
                          f"value: {last_active_sample}")
            
            # Check if session is not expired
            expires_at = session.get(EXPIRES_AT)
            if expires_at:
                try:
                    if expires_at > now:
                        user_id = session.get(USER_ID)
                        if user_id:
                            active_users.add(user_id)
                    else:
                        expired_count += 1
                except TypeError as e:
                    print(f"ERROR: TypeError when comparing expires_at. "
                          f"expires_at type: {type(expires_at).__name__}, "
                          f"now type: {type(now).__name__}, "
                          f"expires_at tzinfo: {getattr(expires_at, 'tzinfo', None)}, "
                          f"now tzinfo: {now.tzinfo}, "
                          f"Error: {e}")
                    raise
            else:
                missing_expires_at += 1
                
            # Categorize by last_active hour
            last_active = session.get(LAST_ACTIVE)
            if last_active:
                try:
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
                except TypeError as e:
                    print(f"ERROR: TypeError when calculating time since last_active. "
                          f"last_active type: {type(last_active).__name__}, "
                          f"now type: {type(now).__name__}, "
                          f"Error: {e}")
                    raise
            else:
                missing_last_active += 1
        
        sorted_breakdown = dict(sorted(last_active_by_hour.items()))
        
        # Log summary statistics
        print(f"Processing complete:")
        print(f"  - Active users: {len(active_users)}")
        print(f"  - Expired sessions: {expired_count}")
        print(f"  - Sessions missing expires_at: {missing_expires_at}")
        print(f"  - Sessions missing last_active: {missing_last_active}")
        print(f"  - Last active breakdown: {sorted_breakdown}")
        
        response = {
            STATUS: SUCCESS,
            ACTIVE_USERS_COUNT: len(active_users),
            TOTAL_SESSIONS: len(sessions),
            LAST_ACTIVE_BREAKDOWN: sorted_breakdown,
            TIMESTAMP: now.isoformat(),
        }
        
        print(f"Returning successful response with {len(response)} fields")
        return response, 200

    except Exception as e:
        print(f"EXCEPTION in get_sessions_overview: {type(e).__name__}: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        
        error_response = {
            STATUS: ERROR,
            MESSAGE: str(e),
            ERROR_TYPE: type(e).__name__,
        }
        return error_response, 500

