"""Cloud Function to get active sessions for a user.

This function queries Datastore for active (non-expired) sessions for a given user.
Used by Flask-Login's @login_required decorator.
"""

import functions_framework
from datetime import datetime
from shared import datastore_client


@functions_framework.http
def get_user_session(request):
    """
    HTTP Cloud Function to get active session for a user.
    
    Args:
        request (flask.Request): HTTP request object with JSON body or query params
        
    Expected JSON body or query params:
        {
            "user_id": "string"
        }
    
    Returns:
        JSON response with user session data
    """
    try:
        # Try JSON body first, then query params
        request_json = request.get_json(silent=True)
        
        if request_json:
            user_id = request_json.get("user_id")
        else:
            user_id = request.args.get("user_id")
        
        if not user_id:
            return {
                "status": "error",
                "message": "Missing required field: user_id"
            }, 400
        
        # Query for active sessions
        db = datastore_client.get_datastore_client()
        query = db.query(kind="Session")
        query.add_filter("user_id", "=", user_id)
        query.add_filter("expires_at", ">", datetime.now())
        
        sessions = list(query.fetch(limit=1))
        
        if not sessions:
            return {
                "status": "error",
                "message": "No active session found",
                "has_session": False
            }, 404
        
        session = sessions[0]
        
        # Return user data from session
        response = {
            "status": "success",
            "has_session": True,
            "user_id": session.get("user_id"),
            "email": session.get("email"),
            "name": session.get("name"),
            "picture": session.get("picture"),
            "created_at": session.get("created_at").isoformat() if session.get("created_at") else None,
            "last_active": session.get("last_active").isoformat() if session.get("last_active") else None,
            "expires_at": session.get("expires_at").isoformat() if session.get("expires_at") else None
        }
        
        return response, 200
        
    except Exception as e:
        print(f"Error getting user session: {e}")
        return {
            "status": "error",
            "message": str(e),
            "error_type": type(e).__name__,
        }, 500

