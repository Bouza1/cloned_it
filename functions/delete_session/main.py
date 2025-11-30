"""Cloud Function to delete a user session from Datastore.

This function handles session deletion (logout) with audit logging.
"""

import functions_framework
from shared import datastore_client


@functions_framework.http
def delete_session(request):
    """
    HTTP Cloud Function to delete a user session.
    
    Args:
        request (flask.Request): HTTP request object with JSON body
        
    Expected JSON body:
        {
            "session_id": "string",
            "reason": "string (optional)" - e.g., "logout", "expired", "security_violation"
        }
    
    Returns:
        JSON response with deletion status
    """
    try:
        # Parse request body
        request_json = request.get_json(silent=True)
        
        if not request_json:
            return {
                "status": "error",
                "message": "Request body must be JSON"
            }, 400
        
        # Extract session_id
        session_id = request_json.get("session_id")
        
        if not session_id:
            return {
                "status": "error",
                "message": "Missing required field: session_id"
            }, 400
        
        reason = request_json.get("reason", "logout")
        
        # Get session from Datastore
        db = datastore_client.get_datastore_client()
        key = db.key("Session", session_id)
        session = db.get(key)
        
        if not session:
            return {
                "status": "error",
                "message": "Session not found",
                "deleted": False
            }, 404
        
        user_id = session.get("user_id")
        
        # Delete the session
        db.delete(key)
        
        print(f"Session deleted: {session_id[:8]}... for user {user_id}, reason: {reason}")
        
        response = {
            "status": "success",
            "deleted": True,
            "session_id": session_id[:8] + "...",
            "user_id": user_id,
            "reason": reason
        }
        
        return response, 200
        
    except Exception as e:
        print(f"Error deleting session: {e}")
        return {
            "status": "error",
            "message": str(e),
            "error_type": type(e).__name__,
        }, 500

