"""
Security decorators for route protection with automatic logging.

These decorators provide authorization checks with automatic security logging.
"""

from functools import wraps
from typing import Callable, Optional

from flask import g, jsonify, request
from flask_login import current_user

from app.utils.logging.security_logger import (
    SecurityEventType,
    log_access_decision,
)


def require_auth(f: Callable) -> Callable:
    """
    Require authentication with security logging.

    Logs both granted and denied access attempts.
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            # Log access denied
            log_access_decision(
                resource=request.path,
                action=request.method,
                granted=False,
                reason="Not authenticated",
            )
            return jsonify({"error": "Authentication required"}), 401

        # Log access granted
        log_access_decision(
            resource=request.path,
            action=request.method,
            granted=True,
            user_id=current_user.id,
        )

        return f(*args, **kwargs)

    return decorated_function


def require_role(role: str) -> Callable:
    """
    Require specific role with security logging.

    Args:
        role: Required role (e.g., "admin", "moderator")

    Usage:
        @app.route('/admin/users')
        @login_required
        @require_role('admin')
        def admin_users():
            ...
    """

    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                log_access_decision(
                    resource=request.path,
                    action=request.method,
                    granted=False,
                    reason="Not authenticated",
                    required_role=role,
                )
                return jsonify({"error": "Authentication required"}), 401

            # Check if user has required role
            # TODO: Implement user.has_role() method in User model
            user_role = getattr(current_user, "role", None)
            if user_role != role:
                log_access_decision(
                    resource=request.path,
                    action=request.method,
                    granted=False,
                    user_id=current_user.id,
                    reason=f"Insufficient permissions: requires {role}, has {user_role}",
                    required_role=role,
                    user_role=user_role,
                )
                return jsonify({"error": "Insufficient permissions"}), 403

            # Log access granted
            log_access_decision(
                resource=request.path,
                action=request.method,
                granted=True,
                user_id=current_user.id,
                required_role=role,
                user_role=user_role,
            )

            return f(*args, **kwargs)

        return decorated_function

    return decorator


def require_permission(permission: str) -> Callable:
    """
    Require specific permission with security logging.

    Args:
        permission: Required permission (e.g., "users:write", "posts:delete")

    Usage:
        @app.route('/api/users/<user_id>', methods=['DELETE'])
        @login_required
        @require_permission('users:delete')
        def delete_user(user_id):
            ...
    """

    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                log_access_decision(
                    resource=request.path,
                    action=request.method,
                    granted=False,
                    reason="Not authenticated",
                    required_permission=permission,
                )
                return jsonify({"error": "Authentication required"}), 401

            # Check if user has required permission
            # Note: Implement user.has_permission() method in your User model
            has_permission = getattr(
                current_user, "has_permission", lambda p: False
            )(permission)

            if not has_permission:
                log_access_decision(
                    resource=request.path,
                    action=request.method,
                    granted=False,
                    user_id=current_user.id,
                    reason=f"Missing required permission: {permission}",
                    required_permission=permission,
                )
                return jsonify({"error": "Insufficient permissions"}), 403

            # Log access granted
            log_access_decision(
                resource=request.path,
                action=request.method,
                granted=True,
                user_id=current_user.id,
                required_permission=permission,
            )

            return f(*args, **kwargs)

        return decorated_function

    return decorator


def rate_limit_with_logging(
    max_attempts: int = 5, window_seconds: int = 60
) -> Callable:
    """
    Rate limit endpoint with security logging for violations.

    Args:
        max_attempts: Maximum attempts allowed in window
        window_seconds: Time window in seconds

    Usage:
        @app.route('/api/login', methods=['POST'])
        @rate_limit_with_logging(max_attempts=5, window_seconds=60)
        def login():
            ...

    TODO: Use a proper rate limiting library like Flask-Limiter with Redis backend.
    """

    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from datetime import datetime, timedelta

            from app.utils.logging.security_logger import (
                log_security_violation,
            )

            # Simple in-memory rate limiting (use Redis in production!)
            if not hasattr(g, "rate_limit_store"):
                g.rate_limit_store = {}

            # Create key based on IP and endpoint
            key = f"{request.remote_addr}:{request.path}"
            now = datetime.now()
            cutoff = now - timedelta(seconds=window_seconds)

            # Get attempts for this key
            attempts = g.rate_limit_store.get(key, [])
            # Filter to only recent attempts
            attempts = [t for t in attempts if t > cutoff]

            if len(attempts) >= max_attempts:
                # Rate limit exceeded - log security violation
                log_security_violation(
                    SecurityEventType.SUSPICIOUS_ACTIVITY,
                    severity="medium",
                    description=f"Rate limit exceeded: {len(attempts)} attempts in {window_seconds}s",
                    user_id=(
                        getattr(current_user, "id", None)
                        if current_user.is_authenticated
                        else None
                    ),
                    endpoint=request.path,
                    max_attempts=max_attempts,
                    window_seconds=window_seconds,
                    actual_attempts=len(attempts),
                )
                return jsonify({"error": "Rate limit exceeded"}), 429

            # Record this attempt
            attempts.append(now)
            g.rate_limit_store[key] = attempts

            return f(*args, **kwargs)

        return decorated_function

    return decorator
