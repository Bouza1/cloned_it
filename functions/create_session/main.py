"""Cloud Function to create a new user session in Datastore.

This function creates a secure session with:
- Cryptographically secure session ID (256-bit)
- Session binding via IP and User-Agent hashing
- 30-day expiration
- Audit logging
"""

import hashlib
import secrets
import functions_framework
from datetime import datetime, timedelta
from google.cloud import datastore
from shared import datastore_client


@functions_framework.http
def create_session(request):
    """
    HTTP Cloud Function to create a new user session.
    
    Args:
        request (flask.Request): HTTP request object with JSON body
        
    Expected JSON body:
        {
            "user_id": "string",
            "email": "string",
            "name": "string",
            "picture": "string (optional)",
            "ip_address": "string (optional)",
            "user_agent": "string (optional)"
        }
    
    Returns:
        JSON response with session_id and session data
    """
    try:
        # Parse request body
        request_json = request.get_json(silent=True)
        
        if not request_json:
            return {
                "status": "error",
                "message": "Request body must be JSON"
            }, 400
        
        # Extract required fields
        user_id = request_json.get("user_id")
        email = request_json.get("email")
        name = request_json.get("name")
        
        if not all([user_id, email, name]):
            return {
                "status": "error",
                "message": "Missing required fields: user_id, email, name"
            }, 400
        
        # Optional fields
        picture = request_json.get("picture")
        ip_address = request_json.get("ip_address")
        user_agent = request_json.get("user_agent")
        
        # Generate secure session ID
        session_id = secrets.token_urlsafe(32)
        
        # Hash IP and User-Agent for session binding
        ip_hash = None
        ua_hash = None
        
        if ip_address:
            ip_hash = hashlib.sha256(ip_address.encode()).hexdigest()[:16]
        
        if user_agent:
            ua_hash = hashlib.sha256(user_agent.encode()).hexdigest()[:16]
        
        # Minimal session data
        now = datetime.now()
        session_data = {
            "user_id": user_id,
            "email": email,
            "name": name,
            "picture": picture,
            "created_at": now,
            "last_active": now,
            "expires_at": now + timedelta(days=30),
            "ip_hash": ip_hash,
            "ua_hash": ua_hash,
        }
        
        # Store in Datastore
        db = datastore_client.get_datastore_client()
        key = db.key("Session", session_id)
        entity = datastore.Entity(key=key)
        entity.update(session_data)
        db.put(entity)
        
        print(f"Session created: {session_id[:8]}... for user {user_id}")
        
        response = {
            "status": "success",
            "session_id": session_id,
            "user_id": user_id,
            "expires_at": session_data["expires_at"].isoformat(),
            "created_at": now.isoformat(),
        }
        
        return response, 201
        
    except Exception as e:
        print(f"Error creating session: {e}")
        return {
            "status": "error",
            "message": str(e),
            "error_type": type(e).__name__,
        }, 500

