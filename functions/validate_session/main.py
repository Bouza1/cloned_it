"""Cloud Function to validate a user session in Datastore.

This function validates sessions and checks for hijacking attempts:
- Session exists and not expired
- IP address hasn't changed (if provided)
- User-Agent hasn't changed (if provided)
- Updates last_active timestamp on successful validation
"""

import hashlib
import functions_framework
from datetime import datetime, timezone
from shared import datastore_client


@functions_framework.http
def validate_session(request):
    """
    HTTP Cloud Function to validate a user session.
    
    Args:
        request (flask.Request): HTTP request object with JSON body
        
    Expected JSON body:
        {
            "session_id": "string",
            "ip_address": "string (optional)",
            "user_agent": "string (optional)"
        }
    
    Returns:
        JSON response with validation result and user data
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
        
        # Optional security fields
        ip_address = request_json.get("ip_address")
        user_agent = request_json.get("user_agent")
        
        # Get session from Datastore
        db = datastore_client.get_datastore_client()
        key = db.key("Session", session_id)
        session = db.get(key)
        
        if not session:
            return {
                "status": "error",
                "message": "Session not found",
                "valid": False
            }, 404
        
        # Check expiration (use timezone-aware datetime)
        expires_at = session.get("expires_at")
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at)
        
        if expires_at < datetime.now(timezone.utc):
            # Session expired - delete it
            db.delete(key)
            print(f"Session expired and deleted: {session_id[:8]}...")
            return {
                "status": "error",
                "message": "Session expired",
                "valid": False,
                "reason": "expired"
            }, 401
        
        # Security validation
        violation = None
        
        if ip_address:
            current_ip_hash = hashlib.sha256(ip_address.encode()).hexdigest()[:16]
            stored_ip_hash = session.get("ip_hash")
            
            if stored_ip_hash and stored_ip_hash != current_ip_hash:
                # IP changed - potential hijacking
                db.delete(key)
                violation = "ip_mismatch"
                print(f"Session deleted due to IP mismatch: {session_id[:8]}...")
                return {
                    "status": "error",
                    "message": "IP address mismatch - possible session hijacking",
                    "valid": False,
                    "reason": "ip_mismatch"
                }, 401
        
        if user_agent:
            current_ua_hash = hashlib.sha256(user_agent.encode()).hexdigest()[:16]
            stored_ua_hash = session.get("ua_hash")
            
            if stored_ua_hash and stored_ua_hash != current_ua_hash:
                # User-Agent changed - potential hijacking
                db.delete(key)
                violation = "user_agent_mismatch"
                print(f"Session deleted due to User-Agent mismatch: {session_id[:8]}...")
                return {
                    "status": "error",
                    "message": "User-Agent mismatch - possible session hijacking",
                    "valid": False,
                    "reason": "user_agent_mismatch"
                }, 401
        
        # Update last_active timestamp (use timezone-aware datetime)
        session["last_active"] = datetime.now(timezone.utc)
        db.put(session)
        
        # Return validated session data
        response = {
            "status": "success",
            "valid": True,
            "user_id": session.get("user_id"),
            "email": session.get("email"),
            "name": session.get("name"),
            "picture": session.get("picture"),
            "created_at": session.get("created_at").isoformat() if session.get("created_at") else None,
            "last_active": session.get("last_active").isoformat() if session.get("last_active") else None,
            "expires_at": expires_at.isoformat()
        }
        
        return response, 200
        
    except Exception as e:
        print(f"Error validating session: {e}")
        return {
            "status": "error",
            "message": str(e),
            "error_type": type(e).__name__,
        }, 500

