import os

from flask import Blueprint, current_app, jsonify

from app.constants import FLASK_ENV, PRODUCTION, SECRET_KEY

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    app_secret = current_app.config.get(SECRET_KEY)
    app_environment = os.environ.get(FLASK_ENV, PRODUCTION)

    return jsonify(
        {
            "message": "App!",
            "secret_key": app_secret,
            "environment": app_environment,
        }
    )
