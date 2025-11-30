"""Helper module for calling session management Cloud Functions.

This module provides a clean interface for the User model to interact with
session management Cloud Functions instead of directly accessing Datastore.
"""

import requests
import google.auth
import google.auth.transport.requests
from google.oauth2 import id_token
from typing import Optional, Dict, Any

from app.utils.cloud_functions import get_function_url
from app.utils.logging.logger import get_logger

logger = get_logger(__name__)


def create_session_remote(
    user_id: str,
    email: str,
    name: str,
    picture: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
) -> Optional[str]:
    """
    Create a session via Cloud Function.
    
    Args:
        user_id: User ID
        email: User email
        name: User name
        picture: User picture URL
        ip_address: Client IP address for session binding
        user_agent: Client User-Agent for session binding
        
    Returns:
        session_id if successful, None otherwise
    """
    try:
        function_url = get_function_url("create_session")
        
        # Get credentials and generate ID token
        auth_req = google.auth.transport.requests.Request()
        id_token_credential = id_token.fetch_id_token(auth_req, function_url)
        
        headers = {"Authorization": f"Bearer {id_token_credential}"}
        payload = {
            "user_id": user_id,
            "email": email,
            "name": name,
            "picture": picture,
            "ip_address": ip_address,
            "user_agent": user_agent
        }
        
        response = requests.post(function_url, json=payload, headers=headers, timeout=10)
        
        if response.status_code == 201:
            data = response.json()
            if data.get("status") == "success":
                logger.info(f"Session created for user {user_id}")
                return data.get("session_id")
        
        logger.error(f"Failed to create session: {response.status_code}")
        return None
        
    except Exception as e:
        logger.error(f"Error creating session: {e}", exc_info=True)
        return None


def validate_session_remote(
    session_id: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Validate a session via Cloud Function.
    
    Args:
        session_id: Session ID to validate
        ip_address: Client IP address for validation
        user_agent: Client User-Agent for validation
        
    Returns:
        User data dict if valid, None otherwise
    """
    try:
        function_url = get_function_url("validate_session")
        
        # Get credentials and generate ID token
        auth_req = google.auth.transport.requests.Request()
        id_token_credential = id_token.fetch_id_token(auth_req, function_url)
        
        headers = {"Authorization": f"Bearer {id_token_credential}"}
        payload = {
            "session_id": session_id,
            "ip_address": ip_address,
            "user_agent": user_agent
        }
        
        response = requests.post(function_url, json=payload, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "success" and data.get("valid"):
                logger.info(f"Session validated: {session_id[:8]}...")
                return {
                    "user_id": data.get("user_id"),
                    "email": data.get("email"),
                    "name": data.get("name"),
                    "picture": data.get("picture")
                }
        
        logger.warning(f"Session validation failed: {response.status_code}")
        return None
        
    except Exception as e:
        logger.error(f"Error validating session: {e}", exc_info=True)
        return None


def delete_session_remote(session_id: str, reason: str = "logout") -> bool:
    """
    Delete a session via Cloud Function.
    
    Args:
        session_id: Session ID to delete
        reason: Reason for deletion
        
    Returns:
        True if successful, False otherwise
    """
    try:
        function_url = get_function_url("delete_session")
        
        # Get credentials and generate ID token
        auth_req = google.auth.transport.requests.Request()
        id_token_credential = id_token.fetch_id_token(auth_req, function_url)
        
        headers = {"Authorization": f"Bearer {id_token_credential}"}
        payload = {
            "session_id": session_id,
            "reason": reason
        }
        
        response = requests.post(function_url, json=payload, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "success":
                logger.info(f"Session deleted: {session_id[:8]}..., reason: {reason}")
                return True
        
        logger.error(f"Failed to delete session: {response.status_code}")
        return False
        
    except Exception as e:
        logger.error(f"Error deleting session: {e}", exc_info=True)
        return False


def get_user_session_remote(user_id: str) -> Optional[Dict[str, Any]]:
    """
    Get user session via Cloud Function.
    
    Args:
        user_id: User ID
        
    Returns:
        User data dict if session exists, None otherwise
    """
    try:
        function_url = get_function_url("get_user_session")
        
        # Get credentials and generate ID token
        auth_req = google.auth.transport.requests.Request()
        id_token_credential = id_token.fetch_id_token(auth_req, function_url)
        
        headers = {"Authorization": f"Bearer {id_token_credential}"}
        params = {"user_id": user_id}
        
        response = requests.get(function_url, params=params, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "success" and data.get("has_session"):
                logger.info(f"User session found for {user_id}")
                return {
                    "user_id": data.get("user_id"),
                    "email": data.get("email"),
                    "name": data.get("name"),
                    "picture": data.get("picture")
                }
        
        logger.info(f"No active session for user {user_id}")
        return None
        
    except Exception as e:
        logger.error(f"Error getting user session: {e}", exc_info=True)
        return None

