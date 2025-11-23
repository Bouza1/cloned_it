import os

from flask import Blueprint, render_template
from flask_login import login_required

from app.constants import FLASK_ENV, MAIN, PRODUCTION, PROFILE
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
