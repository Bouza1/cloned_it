"""
This module provides structured logging with:
- Google Cloud Logging integration
- Request correlation IDs
- Environment-specific log levels
- Structured JSON output
- Error tracking
"""

import contextvars
import logging
import os
import sys
from typing import Any, Optional

import google.cloud.logging
from flask import Flask, g, has_request_context, request
from google.cloud.logging_v2.handlers import CloudLoggingHandler, setup_logging

from app.constants import (
    DEVELOPMENT,
    ENVIRONMENT,
    ID,
    LOCAL,
    MESSAGE,
    PRODUCTION,
    USER,
)
from app.utils.logging.constants import (
    ANONYMOUS,
    CORRELATION_ID,
    EXCEPTION,
    LOG_LEVEL,
    LOG_LEVELS,
    LOG_REQUEST_KEYS,
    LOGGER,
    METHOD,
    NO_REQUEST,
    PATH,
    REMOTE_ADDR,
    REQUEST,
    REQUEST_METHOD,
    REQUEST_PATH,
    RESPONSE_SIZE,
    SEVERITY,
    STATUS_CODE,
    UNKNOWN,
    USER_AGENT,
    USER_AGENT_HEADER,
    USER_ID,
    X_CORRELATION_ID,
)

# Context variable for storing correlation ID across async operations
_correlation_id = contextvars.ContextVar(CORRELATION_ID, default=None)


class RequestContextFilter(logging.Filter):
    """
    Logging filter that adds request context information to log records.

    Adds the following fields:
    - correlation_id: Unique ID to trace related logs
    - request_path: The request URL path
    - request_method: HTTP method (GET, POST, etc.)
    - user_agent: Client user agent string
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """Add request context to log record if available."""
        # Add correlation ID
        correlation_id = _correlation_id.get()
        if correlation_id:
            record.correlation_id = correlation_id
        else:
            record.correlation_id = NO_REQUEST

        # Add request information if within request context
        if has_request_context():
            record.request_path = request.path
            record.request_method = request.method
            record.user_agent = request.headers.get(USER_AGENT_HEADER, UNKNOWN)

            # Add user ID if authenticated
            if hasattr(g, USER) and g.user:
                record.user_id = getattr(g.user, ID, UNKNOWN)
            else:
                record.user_id = ANONYMOUS
        else:
            record.request_path = NO_REQUEST
            record.request_method = NO_REQUEST
            record.user_agent = NO_REQUEST
            record.user_id = NO_REQUEST

        return True


class StructuredFormatter(logging.Formatter):
    """
    Custom formatter for structured logging.

    Formats logs with consistent structure including:
    - timestamp
    - severity level
    - correlation ID
    - message
    - request context
    - additional fields
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record with structured fields."""
        # Base log message with structured fields
        log_data = {
            SEVERITY: record.levelname,
            MESSAGE: record.getMessage(),
            LOGGER: record.name,
            CORRELATION_ID: getattr(record, CORRELATION_ID, NO_REQUEST),
        }

        # Add request context if available
        if hasattr(record, REQUEST_PATH):
            log_data[REQUEST] = {
                PATH: record.request_path,
                METHOD: record.request_method,
                USER_AGENT: record.user_agent,
            }

        # Add user context if available
        if hasattr(record, USER_ID):
            log_data[USER_ID] = record.user_id

        # Add exception info if present
        if record.exc_info:
            log_data[EXCEPTION] = self.formatException(record.exc_info)

        # Add extra fields from record
        for key, value in record.__dict__.items():
            if key not in LOG_REQUEST_KEYS:
                log_data[key] = value

        # Format as structured log entry
        return f"{super().format(record)} | {log_data}"


def get_log_level(environment: str) -> int:
    """
    Get appropriate log level based on environment.

    Args:
        environment: The environment name (local, development, production)

    Returns:
        Logging level constant (INFO, WARNING, ERROR, etc.)
    """
    # Allow override via environment variable
    env_log_level = os.environ.get(LOG_LEVEL, "").upper()
    if env_log_level in LOG_LEVELS:
        return getattr(logging, env_log_level)

    # Default levels per environment
    levels = {
        LOCAL: logging.DEBUG,
        DEVELOPMENT: logging.INFO,
        PRODUCTION: logging.WARNING,
    }
    return levels.get(environment, logging.INFO)


def setup_cloud_logging(environment: str) -> None:
    """
    Configure Google Cloud Logging for App Engine.

    Args:
        environment: The environment name (local, development, production)
    """
    # Only enable Cloud Logging for deployed environments
    if environment in (DEVELOPMENT, PRODUCTION):
        try:
            # Initialize Google Cloud Logging client
            client = google.cloud.logging.Client()

            # Set up Cloud Logging handler with automatic resource detection
            handler = CloudLoggingHandler(client)

            # Integrate with Python's logging
            setup_logging(handler)

            logging.info(
                f"Google Cloud Logging initialized for {environment} environment"
            )
        except Exception as e:
            # Fallback to standard logging if Cloud Logging setup fails
            logging.error(
                f"Failed to initialize Google Cloud Logging: {e}. "
                "Falling back to standard logging."
            )
            setup_local_logging(environment)
    else:
        setup_local_logging(environment)


def setup_local_logging(environment: str) -> None:
    """
    Configure local logging for development/testing.

    Args:
        environment: The environment name
    """
    log_level = get_log_level(environment)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create console handler with structured formatter
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)

    # Use structured formatter for consistency
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | "
        "[%(correlation_id)s] | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(formatter)
    console_handler.addFilter(RequestContextFilter())

    root_logger.addHandler(console_handler)

    # Reduce noise from third-party libraries
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("google").setLevel(logging.WARNING)

    logging.info(f"Local logging configured for {environment} environment")


def configure_logging(app: Flask) -> None:
    """
    Configure application-wide logging based on environment.

    Args:
        app: Flask application instance
    """
    environment = app.config.get(ENVIRONMENT, LOCAL)

    # Set up appropriate logging backend
    if environment in (DEVELOPMENT, PRODUCTION):
        setup_cloud_logging(environment)
    else:
        setup_local_logging(environment)

    # Register request context hooks
    setup_request_logging(app)


def setup_request_logging(app: Flask) -> None:
    """
    Set up request-level logging hooks.

    Args:
        app: Flask application instance
    """

    @app.before_request
    def before_request_logging():
        """Log request start and set correlation ID."""
        import uuid

        # Generate or extract correlation ID
        correlation_id = request.headers.get(
            X_CORRELATION_ID, str(uuid.uuid4())
        )
        _correlation_id.set(correlation_id)
        g.correlation_id = correlation_id

        # Log request start
        logger = logging.getLogger("app.request")
        logger.info(
            f"Request started: {request.method} {request.path}",
            extra={
                CORRELATION_ID: correlation_id,
                REMOTE_ADDR: request.remote_addr,
                USER_AGENT: request.headers.get(USER_AGENT_HEADER),
            },
        )

    @app.after_request
    def after_request_logging(response):
        """Log request completion."""
        logger = logging.getLogger("app.request")

        # Log response
        logger.info(
            f"Request completed: {request.method} {request.path} - "
            f"Status: {response.status_code}",
            extra={
                CORRELATION_ID: g.get(CORRELATION_ID, UNKNOWN),
                STATUS_CODE: response.status_code,
                RESPONSE_SIZE: response.content_length,
            },
        )

        # Add correlation ID to response headers for client tracking
        response.headers[X_CORRELATION_ID] = g.get(CORRELATION_ID, UNKNOWN)

        return response

    @app.errorhandler(Exception)
    def handle_exception(e: Exception):
        """Log unhandled exceptions."""
        from werkzeug.exceptions import HTTPException

        logger = logging.getLogger("app.error")

        # Don't log HTTP exceptions (404, 403, etc.) as errors
        # These are normal HTTP responses, not application errors
        if isinstance(e, HTTPException):
            # Only log at INFO level for client errors (4xx) without stack trace
            if 400 <= e.code < 500:
                logger.info(
                    f"HTTP {e.code}: {e.name} - {request.method} {request.path}",
                    extra={
                        CORRELATION_ID: g.get(CORRELATION_ID, UNKNOWN),
                        REQUEST_PATH: request.path,
                        REQUEST_METHOD: request.method,
                        STATUS_CODE: e.code,
                    },
                )
            # Log server errors (5xx) at ERROR level
            else:
                logger.error(
                    f"HTTP {e.code}: {e.name} - {request.method} {request.path}",
                    extra={
                        CORRELATION_ID: g.get(CORRELATION_ID, UNKNOWN),
                        REQUEST_PATH: request.path,
                        REQUEST_METHOD: request.method,
                        STATUS_CODE: e.code,
                    },
                )
        else:
            # Log actual exceptions (not HTTP errors) at ERROR with stack trace
            logger.error(
                f"Unhandled exception: {str(e)}",
                exc_info=True,
                extra={
                    CORRELATION_ID: g.get(CORRELATION_ID, UNKNOWN),
                    REQUEST_PATH: request.path,
                    REQUEST_METHOD: request.method,
                },
            )

        # Re-raise to allow Flask's default error handling
        raise


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name.

    This is a convenience wrapper around logging.getLogger that ensures
    consistent logger configuration.

    Args:
        name: Logger name (typically __name__ of the module)

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


def log_with_context(
    logger: logging.Logger, level: str, message: str, **kwargs: Any
) -> None:
    """
    Log a message with additional context.

    Args:
        logger: Logger instance to use
        level: Log level (debug, info, warning, error, critical)
        message: Log message
        **kwargs: Additional context to include in log
    """
    log_func = getattr(logger, level.lower())
    log_func(message, extra=kwargs)
