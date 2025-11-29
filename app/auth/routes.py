"""Authentication routes for Google OAuth with secure session management."""

from authlib.integrations.flask_client import OAuth
from flask import Blueprint, redirect, request, session, url_for
from flask_login import login_required, login_user, logout_user

from app.constants import (
    API,
    AUTH,
    CALLBACK,
    EMAIL,
    ID,
    LOGIN,
    LOGOUT,
    MESSAGE,
    NAME,
    PICTURE,
    PROFILE,
    SUB,
    USER,
    USER_INFO,
)
from app.models.user import User
from app.utils.logging.constants import UNKNOWN, USER_EMAIL, USER_ID
from app.utils.logging.logger import get_logger
from app.utils.logging.security_logger import (
    SecurityEventType,
    log_account_created,
    log_auth_event,
    log_login_success,
    log_logout,
)

auth_bp = Blueprint(AUTH, __name__, url_prefix=f"/{AUTH}")

# OAuth is initialized in app/__init__.py
oauth = OAuth()

logger = get_logger(__name__)  # Application logger


@auth_bp.route(f"/{LOGIN}")
def login():
    """
    Initiate Google OAuth login flow.

    Redirects to Google's authorization URL.
    """
    logger.info("Initiating Google OAuth login flow")

    # Log security event: OAuth initiated
    log_auth_event(
        SecurityEventType.OAUTH_INITIATED,
        success=True,
        oauth_provider="google",
    )

    # Build the redirect URI
    redirect_uri = url_for("auth.callback", _external=True)

    # Redirect to Google OAuth
    return oauth.google.authorize_redirect(redirect_uri)


@auth_bp.route(f"/{CALLBACK}")
def callback():
    """
    Handle the OAuth callback from Google.

    Exchange authorization code for access token and create user session.
    """
    try:
        # Get access token from Google
        token = oauth.google.authorize_access_token()

        # Log security event: OAuth token exchange
        log_auth_event(
            SecurityEventType.OAUTH_TOKEN_EXCHANGE,
            success=True,
            oauth_provider="google",
        )

        # Get user info from Google
        user_info = token.get(USER_INFO)

        if not user_info:
            logger.warning(
                "Failed to get user info from Google OAuth response"
            )
            log_auth_event(
                SecurityEventType.OAUTH_FAILURE,
                success=False,
                reason="No user info in OAuth response",
                oauth_provider="google",
            )
            return "Failed to get user info from Google", 400

        # Extract user details
        user_id = user_info.get(SUB)  # Google's unique user ID
        email = user_info.get(EMAIL)
        name = user_info.get(NAME)
        picture = user_info.get(PICTURE)

        logger.info(
            f"OAuth callback received for user",
            extra={"user_email": email, "user_id": user_id},
        )

        # Log security event: OAuth callback received
        log_auth_event(
            SecurityEventType.OAUTH_CALLBACK,
            success=True,
            user_id=user_id,
            user_email=email,
            oauth_provider="google",
        )

        # Check if user already exists (check for existing session)
        user = User.get(user_id)

        if not user:
            # Create new user
            logger.info(
                f"Creating new user account",
                extra={"user_email": email, "user_id": user_id},
            )

            # Log security event: New account created
            log_account_created(
                user_id=user_id,
                user_email=email,
                created_by=user_id,  # Self-registration via OAuth
            )
        else:
            logger.info(
                f"Existing user logging in",
                extra={"user_email": email, "user_id": user_id},
            )

        # Create secure session in Datastore
        session_id = User.create_session(
            user_id=user_id,
            email=email,
            name=name,
            picture=picture,
            request=request,  # For IP/UA binding
        )

        # Create User instance for Flask-Login
        user = User.create(
            id_=user_id, email=email, name=name, picture=picture
        )

        # Log the user in (creates Flask-Login session)
        login_user(user)

        # Store minimal user info in Flask session for easy access
        session[USER] = {
            ID: user_id,
            EMAIL: email,
            NAME: name,
            PICTURE: picture,
        }

        logger.info(
            f"User successfully authenticated",
            extra={"user_email": email, "user_id": user_id},
        )

        # Log security event: Login successful
        log_login_success(
            user_id=user_id, user_email=email, oauth_provider="google"
        )

        # Redirect to home page with secure session cookie
        response = redirect(url_for("main.index"))

        # Set secure session cookie
        response.set_cookie(
            "session_id",
            session_id,
            max_age=30 * 24 * 60 * 60,  # 30 days
            secure=True,  # HTTPS only
            httponly=True,  # Prevent XSS
            samesite="Lax",  # Prevent CSRF
        )

        return response

    except Exception as e:
        logger.error(
            f"OAuth authentication failed: {str(e)}",
            exc_info=True,
            extra={"error_type": type(e).__name__},
        )

        # Log security event: OAuth authentication failed
        log_auth_event(
            SecurityEventType.OAUTH_FAILURE,
            success=False,
            reason=str(e),
            error_type=type(e).__name__,
            oauth_provider="google",
        )

        return f"Authentication failed: {str(e)}", 500


@auth_bp.route(f"/{LOGOUT}")
@login_required
def logout():
    """
    Log out the current user.

    Clears the Flask-Login session and user data from session.
    """
    user_data = session.get(USER, {})
    user_id = user_data.get(ID, UNKNOWN)
    user_email = user_data.get(EMAIL, UNKNOWN)

    # Get session ID from cookie
    session_id = request.cookies.get("session_id")

    logger.info(
        f"User logging out", extra={USER_EMAIL: user_email, USER_ID: user_id}
    )

    # Delete session from Datastore
    if session_id:
        User.delete_session(session_id, reason=SecurityEventType.LOGOUT)

    log_logout(user_id=user_id)

    # Clear Flask-Login session
    logout_user()
    session.clear()

    logger.info(
        f"User successfully logged out",
        extra={USER_EMAIL: user_email, USER_ID: user_id},
    )

    # Redirect and clear session cookie
    response = redirect(url_for("main.index"))
    response.set_cookie("session_id", "", expires=0)  # Clear cookie

    return response


@auth_bp.route(f"/{API}/{PROFILE}")
@login_required
def api_profile():
    """
    API endpoint for user profile data.

    Returns JSON with user information.
    """
    user_data = session.get(USER, {})
    return {
        MESSAGE: "User profile",
        USER: {
            ID: user_data.get(ID),
            EMAIL: user_data.get(EMAIL),
            NAME: user_data.get(NAME),
            PICTURE: user_data.get(PICTURE),
        },
    }
