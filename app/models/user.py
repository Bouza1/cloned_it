"""User model for authentication with secure session management.

Session management is now handled via Cloud Functions for better
scalability and separation of concerns.
"""

from flask_login import UserMixin
from app.utils import session_client


class User(UserMixin):
    """
    User model for Google OAuth authentication.

    Sessions are stored securely in Datastore with:
    - Cryptographically secure session IDs
    - Minimal data storage (only user_id reference)
    - Session binding (IP + User-Agent hashing)
    - Automatic expiration
    - Audit logging
    """

    def __init__(
        self,
        id_: str,
        email: str,
        name: str,
        picture: str = None,
    ):
        self.id = id_
        self.email = email
        self.name = name
        self.picture = picture

    @staticmethod
    def get(user_id: str):
        """
        Get a user by ID via Cloud Function.

        Called by Flask-Login's @login_required decorator.
        Only returns user if they have a valid, active session.

        Args:
            user_id: Google OAuth user ID

        Returns:
            User instance if session exists, None otherwise
        """
        user_data = session_client.get_user_session_remote(user_id)
        
        if user_data:
            return User(
                id_=user_data.get("user_id"),
                email=user_data.get("email", ""),
                name=user_data.get("name", ""),
                picture=user_data.get("picture"),
            )
        
        return None

    @staticmethod
    def create_session(
        user_id: str,
        email: str,
        name: str,
        picture: str = None,
        request=None,
    ):
        """
        Create a secure session via Cloud Function.

        Security measures:
        - Cryptographically secure session ID (256-bit)
        - Session binding via IP and User-Agent hashing
        - 30-day expiration

        Args:
            user_id: Google OAuth user ID
            email: User's email
            name: User's display name
            picture: User's profile picture URL
            request: Flask request object (for security binding)

        Returns:
            session_id: Secure session identifier
        """
        ip_address = None
        user_agent = None
        
        if request:
            ip_address = request.remote_addr
            user_agent = request.headers.get("User-Agent", "")
        
        return session_client.create_session_remote(
            user_id=user_id,
            email=email,
            name=name,
            picture=picture,
            ip_address=ip_address,
            user_agent=user_agent
        )

    @staticmethod
    def validate_session(session_id: str, request=None):
        """
        Validate session via Cloud Function and check for hijacking attempts.

        Checks:
        - Session exists
        - Session not expired
        - IP address hasn't changed (if available)
        - User-Agent hasn't changed (if available)

        Args:
            session_id: Session ID from cookie
            request: Flask request object

        Returns:
            User instance if valid, None if invalid/hijacked
        """
        ip_address = None
        user_agent = None
        
        if request:
            ip_address = request.remote_addr
            user_agent = request.headers.get("User-Agent", "")
        
        user_data = session_client.validate_session_remote(
            session_id=session_id,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        if user_data:
            return User(
                id_=user_data.get("user_id"),
                email=user_data.get("email", ""),
                name=user_data.get("name", ""),
                picture=user_data.get("picture"),
            )
        
        return None

    @staticmethod
    def delete_session(session_id: str, reason: str = "logout"):
        """
        Delete a session via Cloud Function (logout).

        Args:
            session_id: Session ID to delete
            reason: Reason for deletion (for audit log)

        Returns:
            True if deleted, False if not found
        """
        return session_client.delete_session_remote(
            session_id=session_id,
            reason=reason
        )

    @staticmethod
    def create(id_: str, email: str, name: str, picture: str = None):
        """
        Create a new user.
            1. Check if user exists in Cloud SQL
            2. Create user in Cloud SQL if new
            3. Create session in Datastore

        Incoming:
            id_: Google OAuth user ID
            email: User's email
            name: User's display name
            picture: User's profile picture URL

        Returns User instance
        """
        return User(id_=id_, email=email, name=name, picture=picture)

    def __repr__(self):
        return f"<User {self.email}>"
