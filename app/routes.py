import os
from datetime import datetime

import requests
from flask import (
    Blueprint,
    render_template,
)
from flask_login import login_required
import google.auth
import google.auth.transport.requests
from google.oauth2 import id_token


from app.constants import FLASK_ENV, MAIN, PRODUCTION, PROFILE
from app.utils.cloud_functions import get_function_url
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


@main_bp.route("/posts")
def posts():
    """
    Posts page showing all posts from Cloud SQL via Cloud Function.
    """
    try:
        # Get the Cloud Function URL
        function_url = get_function_url("get_posts")
        
        logger.info(f"Calling Cloud Function: {function_url}")
        
        # Get credentials and generate ID token
        auth_req = google.auth.transport.requests.Request()
        id_token_credential = id_token.fetch_id_token(auth_req, function_url)
        
        # Call the Cloud Function with authentication
        headers = {"Authorization": f"Bearer {id_token_credential}"}
        
        # Add query parameters for pagination and sorting
        params = {
            "limit": 20,
            "order_by": "created_at",
            "order": "desc"
        }
        
        response = requests.get(function_url, headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "success":
                posts_list = data.get("posts", [])
                logger.info(f"Retrieved {len(posts_list)} posts from Cloud Function")
                return render_template("posts.html", posts=posts_list)
            else:
                logger.error(f"Cloud Function returned error: {data}")
                return render_template(
                    "posts.html",
                    posts=None,
                    error_message="Failed to load posts from database."
                )
        else:
            logger.error(f"Cloud Function returned status {response.status_code}")
            return render_template(
                "posts.html",
                posts=None,
                error_message=f"Error loading posts: Status {response.status_code}"
            )
    
    except requests.exceptions.Timeout:
        logger.error("Cloud Function request timed out")
        return render_template(
            "posts.html",
            posts=None,
            error_message="Request timed out. Please try again later."
        )
    except Exception as e:
        logger.error(f"Error calling Cloud Function: {e}", exc_info=True)
        return render_template(
            "posts.html",
            posts=None,
            error_message=f"Error loading posts: {str(e)}"
        )

@main_bp.route("/admin/stats")
@login_required
def admin_stats():
    """
    Admin dashboard showing session overview via Cloud Function.
    """
    try:
        # Get the Cloud Function URL
        function_url = get_function_url("get_sessions_overview")

        logger.info(f"Calling Cloud Function: {function_url}")

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
