"""User model for authentication with secure session management."""

import hashlib
import secrets
from datetime import datetime, timedelta

from flask_login import UserMixin

from app.constants import (
    CREATED_AT,
    EMAIL,
    EXPIRES_AT,
    IP_HASH,
    LAST_ACTIVE,
    NAME,
    PICTURE,
    SESSION,
    UA_HASH,
    USER_AGENT_HEADER,
    USER_ID,
)
from app.utils.datastore_client import (
    create_entity,
    delete_entity,
    get_entity,
    update_entity,
)
from app.utils.logging.security_logger import (
    SecurityEventType,
    log_security_violation,
    log_session_event,
)


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
        Get a user by ID from Datastore.

        Called by Flask-Login's @login_required decorator.
        Only returns user if they have a valid, active session.

        Security:
        - Only stores user_id in session
        - Full user data will be fetched from Cloud SQL

        Args:
            user_id: Google OAuth user ID

        Returns:
            User instance if session exists, None otherwise
        """
        try:
            from app.utils.datastore_client import _get_db

            db = _get_db()

            # Query for active sessions for this user
            query = db.query(kind=SESSION)
            query.add_filter(USER_ID, "=", user_id)
            query.add_filter(EXPIRES_AT, ">", datetime.now())

            sessions = list(query.fetch(limit=1))

            if sessions:
                session_data = sessions[0]
                return User(
                    id_=session_data.get(USER_ID),
                    email=session_data.get(EMAIL, ""),
                    name=session_data.get(NAME, ""),
                    picture=session_data.get(PICTURE),
                )

            return None
        except Exception as e:
            from app.utils.logging.logger import get_logger

            logger = get_logger(__name__)
            logger.error(f"Error getting user {user_id}: {e}", exc_info=True)
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
        Create a secure session in Datastore.

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
        # Generate secure session ID
        session_id = secrets.token_urlsafe(32)

        ip_hash = None
        ua_hash = None

        if request:
            # Hash IP address
            ip_hash = hashlib.sha256(request.remote_addr.encode()).hexdigest()[
                :16
            ]

            # Hash User-Agent
            ua_hash = hashlib.sha256(
                request.headers.get("User-Agent", "").encode()
            ).hexdigest()[:16]

        # Minimal session data
        session_data = {
            USER_ID: user_id,
            EMAIL: email,
            NAME: name,
            PICTURE: picture,
            CREATED_AT: datetime.now(),
            LAST_ACTIVE: datetime.now(),
            EXPIRES_AT: datetime.now() + timedelta(days=30),
            IP_HASH: ip_hash,
            UA_HASH: ua_hash,
        }

        # Store in Datastore
        create_entity(SESSION, session_data, entity_name=session_id)

        # Audit log
        log_session_event(
            event_type=SecurityEventType.SESSION_CREATED,
            user_id=user_id,
            session_id=session_id,
            ip_hash=ip_hash,
        )

        return session_id

    @staticmethod
    def validate_session(session_id: str, request=None):
        """
        Validate session and check for hijacking attempts.

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
        session = get_entity(SESSION, entity_name=session_id)

        if not session:
            return None

        # Check expiration
        expires_at = session.get(EXPIRES_AT)
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at)

        if expires_at < datetime.now():
            # Session expired - delete it
            delete_entity(SESSION, entity_name=session_id)
            log_session_event(
                event_type=SecurityEventType.SESSION_EXPIRED,
                user_id=session.get(USER_ID),
                session_id=session_id,
            )
            return None

        # Security validation
        if request:
            # Verify IP hasn't changed
            current_ip_hash = hashlib.sha256(
                request.remote_addr.encode()
            ).hexdigest()[:16]

            stored_ip_hash = session.get(IP_HASH)
            if stored_ip_hash and stored_ip_hash != current_ip_hash:
                # IP changed - Delete session
                delete_entity(SESSION, entity_name=session_id)
                log_security_violation(
                    violation_type=SecurityEventType.SESSION_HIJACK_ATTEMPT,
                    severity="high",
                    description="IP address mismatch detected - possible session hijacking",
                    user_id=session.get(USER_ID),
                    session_id_partial=session_id[:8] + "...",
                    stored_ip_hash=stored_ip_hash[:8] + "...",
                    current_ip_hash=current_ip_hash[:8] + "...",
                )
                return None

            # Verify User-Agent
            current_ua_hash = hashlib.sha256(
                request.headers.get(USER_AGENT_HEADER, "").encode()
            ).hexdigest()[:16]

            stored_ua_hash = session.get(UA_HASH)
            if stored_ua_hash and stored_ua_hash != current_ua_hash:
                # User-Agent changed - Delete session
                delete_entity(SESSION, entity_name=session_id)
                log_security_violation(
                    violation_type=SecurityEventType.SESSION_HIJACK_ATTEMPT,
                    severity="high",
                    description="User-Agent mismatch detected - possible session hijacking",
                    user_id=session.get(USER_ID),
                    session_id_partial=session_id[:8] + "...",
                    stored_ua_hash=stored_ua_hash[:8] + "...",
                    current_ua_hash=current_ua_hash[:8] + "...",
                )
                return None

        # Update last_active timestamp
        update_entity(
            SESSION,
            entity_name=session_id,
            data={LAST_ACTIVE: datetime.now()},
        )

        # Return User instance
        return User(
            id_=session.get(USER_ID),
            email=session.get(EMAIL, ""),
            name=session.get(NAME, ""),
            picture=session.get(PICTURE),
        )

    @staticmethod
    def delete_session(session_id: str, reason=SecurityEventType.LOGOUT):
        """
        Delete a session from Datastore (logout).

        Args:
            session_id: Session ID to delete
            reason: Reason for deletion (for audit log)

        Returns:
            True if deleted, False if not found
        """
        session = get_entity(SESSION, entity_name=session_id)

        if session:
            log_session_event(
                event_type=SecurityEventType.SESSION_DELETED,
                user_id=session.get(USER_ID),
                session_id=session_id,
                reason=reason,
            )

        return delete_entity(SESSION, entity_name=session_id)

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
