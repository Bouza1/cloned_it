import os
from datetime import datetime

import requests
from flask import (
    Blueprint,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import login_required

from app.constants import FLASK_ENV, MAIN, PRODUCTION, PROFILE
from app.utils.cloud_functions import get_function_url
from app.utils.datastore_client import create_entity, get_kind_data, list_kinds
from app.utils.logging.logger import get_logger

main_bp = Blueprint(MAIN, __name__)
logger = get_logger(__name__)


@main_bp.route("/")
def index():
    """
    Home page route.

    Shows authentication status and provides login/logout links.
    """
    app_environment = os.environ.get(FLASK_ENV, PRODUCTION)
    return render_template("index.html", environment=app_environment)


@main_bp.route(f"/{PROFILE}")
@login_required
def profile():
    """
    User profile page.

    Displays user information and account details.
    """
    return render_template("profile.html")


@main_bp.route("/debug-datastore")
def debug_datastore():
    """
    Debug route to diagnose Datastore connection issues.
    """

    debug_info = {
        "success": False,
        "database_mode": "Datastore Mode",
        "environment": {},
        "connection": {},
        "kinds": {},
    }

    try:
        # Environment info
        debug_info["environment"] = {
            "google_creds_set": bool(
                os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
            ),
            "google_project": os.environ.get("GOOGLE_CLOUD_PROJECT"),
        }

        # Try to connect
        from app.utils.datastore_client import _get_db

        db = _get_db()

        debug_info["connection"] = {
            "status": "connected",
            "project_id": db.project,
        }

        # List all kinds
        kinds = list_kinds()
        debug_info["kinds"]["available"] = kinds
        debug_info["kinds"]["count"] = len(kinds)

        # Get sample data from each kind
        samples = {}
        for kind_name in kinds[:10]:  # Limit to first 10 kinds
            try:
                data = get_kind_data(kind_name, limit=5)
                samples[kind_name] = {
                    "entity_count": len(data),
                    "sample_entity": data[0] if data else None,
                }
            except Exception as kind_error:
                samples[kind_name] = {"error": str(kind_error)}

        debug_info["kinds"]["samples"] = samples
        debug_info["success"] = True

    except Exception as e:
        debug_info["error"] = str(e)
        debug_info["error_type"] = type(e).__name__
        logger.error(f"Error in debug_datastore route: {e}", exc_info=True)

    return jsonify(debug_info)


@main_bp.route("/admin/stats")
@login_required
def admin_stats():
    """
    Admin dashboard showing Datastore statistics via Cloud Function.
    """
    try:
        # Get the Cloud Function URL
        function_url = get_function_url("get_datastore_stats")

        logger.info(f"Calling Cloud Function: {function_url}")

        # Get authentication token for App Engine service account
        import google.auth
        import google.auth.transport.requests
        from google.oauth2 import id_token

        # Get credentials and generate ID token
        auth_req = google.auth.transport.requests.Request()
        id_token_credential = id_token.fetch_id_token(auth_req, function_url)

        # Call the Cloud Function with authentication
        headers = {"Authorization": f"Bearer {id_token_credential}"}
        response = requests.get(function_url, headers=headers, timeout=10)

        if response.status_code == 200:
            stats = response.json()
            return render_template("admin/stats.html", stats=stats, error=None)
        else:
            logger.error(
                f"Cloud Function returned status {response.status_code}"
            )
            return render_template(
                "admin/stats.html",
                stats=None,
                error=f"Cloud Function returned error: {response.status_code}",
            )

    except requests.exceptions.Timeout:
        logger.error("Cloud Function request timed out")
        return render_template(
            "admin/stats.html",
            stats=None,
            error="Request timed out. The Cloud Function may not be deployed yet.",
        )
    except Exception as e:
        logger.error(f"Error calling Cloud Function: {e}", exc_info=True)
        return render_template(
            "admin/stats.html", stats=None, error=f"Error: {str(e)}"
        )


@main_bp.route("/posts")
def posts():
    """
    Posts page - displays all posts in Reddit-style.
    """
    try:
        # Get recent posts from Datastore
        posts_data = get_kind_data("Post", limit=50)

        # Sort by created_at if available (newest first)
        if posts_data:
            posts_data.sort(
                key=lambda x: x.get("created_at", ""), reverse=True
            )

        return render_template("posts.html", posts=posts_data)
    except Exception as e:
        logger.error(f"Error loading posts page: {e}", exc_info=True)
        return render_template(
            "posts.html", posts=[], error_message="Error loading posts"
        )


@main_bp.route("/posts/submit", methods=["POST"])
@login_required
def submit_post():
    """
    Handle post submission for Reddit clone.

    Receives form data, validates it, and stores in Datastore.
    """
    try:
        from flask import session as flask_session

        # Get form data
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()
        category = request.form.get("category", "general")

        # Validate inputs
        if not title or not content:
            logger.warning("Post submission failed: Missing title or content")
            posts_data = get_kind_data("Post", limit=50)
            if posts_data:
                posts_data.sort(
                    key=lambda x: x.get("created_at", ""), reverse=True
                )
            return render_template(
                "posts.html",
                posts=posts_data,
                error_message="Title and content are required",
            )

        # Validate title length
        if len(title) > 300:
            logger.warning(
                f"Post submission failed: Title too long ({len(title)} chars)"
            )
            posts_data = get_kind_data("Post", limit=50)
            if posts_data:
                posts_data.sort(
                    key=lambda x: x.get("created_at", ""), reverse=True
                )
            return render_template(
                "posts.html",
                posts=posts_data,
                error_message="Title must be less than 300 characters",
            )

        # Get user info from session
        user_data = flask_session.get("user", {})
        author_id = user_data.get("id", "anonymous")
        author_name = user_data.get("name", "Anonymous")
        author_email = user_data.get("email", "")

        # Format data for Datastore
        post_data = {
            "title": title,
            "content": content,
            "category": category,
            "author_id": author_id,
            "author_name": author_name,
            "author_email": author_email,
            "upvotes": 0,
            "downvotes": 0,
            "comment_count": 0,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        # Write to Datastore
        result = create_entity("Post", post_data)

        if result:
            logger.info(
                f"Successfully created post with ID: {result.get('id')} by {author_name}"
            )
            # Redirect to posts page to show success
            posts_data = get_kind_data("Post", limit=50)
            if posts_data:
                posts_data.sort(
                    key=lambda x: x.get("created_at", ""), reverse=True
                )
            return render_template(
                "posts.html",
                posts=posts_data,
                success_message=f"Post '{title}' published successfully!",
            )
        else:
            logger.error("Failed to create post")
            posts_data = get_kind_data("Post", limit=50)
            if posts_data:
                posts_data.sort(
                    key=lambda x: x.get("created_at", ""), reverse=True
                )
            return render_template(
                "posts.html",
                posts=posts_data,
                error_message="Failed to create post",
            )

    except Exception as e:
        logger.error(f"Error submitting post: {e}", exc_info=True)
        posts_data = get_kind_data("Post", limit=50)
        if posts_data:
            posts_data.sort(
                key=lambda x: x.get("created_at", ""), reverse=True
            )
        return render_template(
            "posts.html", posts=posts_data, error_message=f"Error: {str(e)}"
        )
