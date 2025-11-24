import os

from flask import Blueprint, jsonify, render_template
from flask_login import login_required

from app.constants import FLASK_ENV, MAIN, PRODUCTION, PROFILE
from app.utils.firestore_client import get_collection_data, get_document
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


@main_bp.route("/test-firestore")
def test_firestore():
    """
    Simple test route to check Firestore connectivity.

    Returns JSON data from a test collection.
    Accessible at: /test-firestore?collection=collection_name
    """
    from flask import request

    # Get collection name from query parameter, default to 'test'
    collection_name = request.args.get("collection", "cloned-it-firestore")

    try:
        data = get_collection_data(collection_name)
        return jsonify(
            {
                "success": True,
                "collection": collection_name,
                "count": len(data),
                "data": data,
            }
        )
    except Exception as e:
        logger.error(f"Error in test_firestore route: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
