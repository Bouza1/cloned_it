"""
Security and authentication event logging.

This module provides specialized logging for security-sensitive events including:
- Authentication attempts (success/failure)
- Authorization decisions
- Account changes
- Session management
- Security violations

Security logs are kept separate from application logs for:
- Audit and compliance requirements
- Security monitoring and alerting
- Incident response and forensics
- Access control (security team vs developers)
"""

import logging
from datetime import datetime
from typing import Any, Optional

from flask import has_request_context, request

from app.utils.logging.constants import (
    ACTION,
    AUDIT_EVENT,
    CHANGED_BY,
    CORRELATION_ID,
    DENIAL_REASON,
    DESCRIPTION,
    EVENT_TYPE,
    FAILURE_REASON,
    GRANTED,
    IP_ADDRESS,
    IP_FORWARDED_FOR,
    REQUEST_METHOD,
    REQUEST_PATH,
    RESOURCE,
    SECURITY_EVENT,
    SECURITY_VIOLATION,
    SESSION_ID_PARTIAL,
    SEVERITY,
    SUCCESS,
    TIMESTAMP,
    USER_AGENT,
    USER_AGENT_HEADER,
    USER_EMAIL,
    USER_ID,
    X_CORRELATION_ID,
    X_FORWARDED_FOR,
)

# Security logger Namespaces
security_logger = logging.getLogger("app.security")
auth_logger = logging.getLogger("app.security.auth")
audit_logger = logging.getLogger("app.security.audit")


class SecurityEventType:
    """Standard security event types for consistent logging."""

    # Authentication events
    LOGIN_ATTEMPT = "login_attempt"
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    LOGOUT = "logout"
    SESSION_CREATED = "session_created"
    SESSION_EXPIRED = "session_expired"

    # Account management events
    ACCOUNT_CREATED = "account_created"
    ACCOUNT_DELETED = "account_deleted"
    ACCOUNT_LOCKED = "account_locked"

    # Authorization events
    ACCESS_GRANTED = "access_granted"
    ACCESS_DENIED = "access_denied"

    # Security violations
    BRUTE_FORCE_DETECTED = "brute_force_detected"
    INVALID_TOKEN = "invalid_token"
    CSRF_VIOLATION = "csrf_violation"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"

    # OAuth specific
    OAUTH_INITIATED = "oauth_initiated"
    OAUTH_CALLBACK = "oauth_callback"
    OAUTH_TOKEN_EXCHANGE = "oauth_token_exchange"
    OAUTH_FAILURE = "oauth_failure"


def _get_request_context() -> dict[str, Any]:
    """Extract security-relevant context from the current request."""
    context = {}

    if has_request_context():
        context.update(
            {
                IP_ADDRESS: request.remote_addr,
                USER_AGENT: request.headers.get(USER_AGENT_HEADER),
                REQUEST_PATH: request.path,
                REQUEST_METHOD: request.method,
            }
        )

        # Add X-Forwarded-For if behind proxy (App Engine)
        forwarded_for = request.headers.get(X_FORWARDED_FOR)
        if forwarded_for:
            context[IP_FORWARDED_FOR] = forwarded_for

        # Add correlation ID if available
        correlation_id = request.headers.get(X_CORRELATION_ID)
        if correlation_id:
            context[CORRELATION_ID] = correlation_id

    return context


def log_auth_event(
    event_type: str,
    success: bool,
    user_id: Optional[str] = None,
    user_email: Optional[str] = None,
    reason: Optional[str] = None,
    **extra_context: Any,
) -> None:
    """
    Log an authentication or authorization event.

    Args:
        event_type: Type of event (use SecurityEventType constants)
        success: Whether the event was successful
        user_id: User ID if applicable
        user_email: User email if applicable (be cautious with PII)
        reason: Reason for failure (if applicable)
        **extra_context: Additional context to include
    """
    log_data = {
        EVENT_TYPE: event_type,
        SUCCESS: success,
        TIMESTAMP: datetime.now().isoformat(),
        SECURITY_EVENT: True,  # Flag for easy filtering
    }

    # Add user information
    if user_id:
        log_data[USER_ID] = user_id
    if user_email:
        # TODO: Make email masking function for privacy in production
        log_data[USER_EMAIL] = user_email

    # Add failure reason
    if not success and reason:
        log_data[FAILURE_REASON] = reason

    # Add request context
    log_data.update(_get_request_context())

    # Add any extra context
    log_data.update(extra_context)

    # Log at appropriate level
    level = logging.INFO if success else logging.WARNING
    message = (
        f"Security event: {event_type} - {'SUCCESS' if success else 'FAILURE'}"
    )

    auth_logger.log(level, message, extra=log_data)


def log_account_change(
    event_type: str,
    user_id: str,
    user_email: Optional[str] = None,
    changed_by: Optional[str] = None,
    changes: Optional[dict[str, Any]] = None,
    **extra_context: Any,
) -> None:
    """
    Log account modification events.

    Args:
        event_type: Type of change (use SecurityEventType constants)
        user_id: ID of user being modified
        user_email: Email of user being modified
        changed_by: ID of user making the change (if different)
        changes: Dictionary of changes made
        **extra_context: Additional context
    """
    log_data = {
        EVENT_TYPE: event_type,
        USER_ID: user_id,
        TIMESTAMP: datetime.now().isoformat(),
        SECURITY_EVENT: True,
        AUDIT_EVENT: True,  # Flag for audit trail
    }

    if user_email:
        log_data[USER_EMAIL] = user_email

    if changed_by:
        log_data[CHANGED_BY] = changed_by

    if changes:
        # Sanitize changes to remove sensitive data
        sanitized_changes = {
            k: v
            for k, v in changes.items()
            if k not in ("password", "secret", "token", "key")
        }
        log_data["changes"] = sanitized_changes

    log_data.update(_get_request_context())
    log_data.update(extra_context)

    message = f"Account change: {event_type} for user {user_id}"
    audit_logger.info(message, extra=log_data)


def log_access_decision(
    resource: str,
    action: str,
    granted: bool,
    user_id: Optional[str] = None,
    reason: Optional[str] = None,
    **extra_context: Any,
) -> None:
    """
    Log authorization decisions (access control).

    Args:
        resource: Resource being accessed (e.g., "/api/admin/users")
        action: Action being attempted (e.g., "read", "write", "delete")
        granted: Whether access was granted
        user_id: User attempting access
        reason: Reason for denial (if applicable)
        **extra_context: Additional context
    """
    log_data = {
        EVENT_TYPE: (
            SecurityEventType.ACCESS_GRANTED
            if granted
            else SecurityEventType.ACCESS_DENIED
        ),
        RESOURCE: resource,
        ACTION: action,
        GRANTED: granted,
        TIMESTAMP: datetime.now().isoformat(),
        SECURITY_EVENT: True,
    }

    if user_id:
        log_data[USER_ID] = user_id

    if not granted and reason:
        log_data[DENIAL_REASON] = reason

    log_data.update(_get_request_context())
    log_data.update(extra_context)

    # Log denials at WARNING level for visibility
    level = logging.INFO if granted else logging.WARNING
    message = (
        f"Access {'granted' if granted else 'denied'}: {action} on {resource}"
    )

    auth_logger.log(level, message, extra=log_data)


def log_security_violation(
    violation_type: str,
    severity: str,
    description: str,
    user_id: Optional[str] = None,
    **extra_context: Any,
) -> None:
    """
    Log security violations and suspicious activities.

    Args:
        violation_type: Type of violation (use SecurityEventType constants)
        severity: Severity level ("low", "medium", "high", "critical")
        description: Description of the violation
        user_id: User ID if known
        **extra_context: Additional context
    """
    log_data = {
        EVENT_TYPE: violation_type,
        SEVERITY: severity.upper(),
        DESCRIPTION: description,
        TIMESTAMP: datetime.now().isoformat(),
        SECURITY_EVENT: True,
        SECURITY_VIOLATION: True,  # Flag for immediate alerting
    }

    if user_id:
        log_data[USER_ID] = user_id

    log_data.update(_get_request_context())
    log_data.update(extra_context)

    # Map severity to log level
    level_map = {
        "low": logging.INFO,
        "medium": logging.WARNING,
        "high": logging.ERROR,
        "critical": logging.CRITICAL,
    }
    level = level_map.get(severity.lower(), logging.WARNING)

    message = f"SECURITY VIOLATION [{severity.upper()}]: {violation_type} - {description}"
    security_logger.log(level, message, extra=log_data)


def log_session_event(
    event_type: str,
    user_id: str,
    session_id: Optional[str] = None,
    **extra_context: Any,
) -> None:
    """
    Log session management events.

    Args:
        event_type: Type of session event
        user_id: User ID
        session_id: Session identifier (if applicable)
        **extra_context: Additional context
    """
    log_data = {
        EVENT_TYPE: event_type,
        USER_ID: user_id,
        TIMESTAMP: datetime.now().isoformat(),
        SECURITY_EVENT: True,
    }

    if session_id:
        # Only log partial session ID for security
        log_data[SESSION_ID_PARTIAL] = (
            session_id[:8] + "..." if len(session_id) > 8 else "***"
        )

    log_data.update(_get_request_context())
    log_data.update(extra_context)

    message = f"Session event: {event_type} for user {user_id}"
    auth_logger.info(message, extra=log_data)


# Convenience functions for common operations


def log_login_success(
    user_id: str, user_email: str, oauth_provider: str = "google"
) -> None:
    """Log successful login."""
    log_auth_event(
        SecurityEventType.LOGIN_SUCCESS,
        success=True,
        user_id=user_id,
        user_email=user_email,
        oauth_provider=oauth_provider,
    )


def log_login_failure(reason: str, user_email: Optional[str] = None) -> None:
    """Log failed login attempt."""
    log_auth_event(
        SecurityEventType.LOGIN_FAILURE,
        success=False,
        user_email=user_email,
        reason=reason,
    )


def log_logout(user_id: str) -> None:
    """Log user logout."""
    log_auth_event(
        SecurityEventType.LOGOUT,
        success=True,
        user_id=user_id,
    )


def log_account_created(
    user_id: str, user_email: str, created_by: Optional[str] = None
) -> None:
    """Log new account creation."""
    log_account_change(
        SecurityEventType.ACCOUNT_CREATED,
        user_id=user_id,
        user_email=user_email,
        changed_by=created_by,
    )
