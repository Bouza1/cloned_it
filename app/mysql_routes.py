"""
Example routes showing how to use MySQL instead of Datastore.
This demonstrates the pattern for migrating from datastore_client to mysql_client.
"""

from datetime import datetime

from flask import Blueprint, jsonify, render_template, request
from flask_login import login_required

from app.utils.logging.logger import get_logger
from app.utils.mysql_client import (
    create_post,
    create_user,
    execute_query,
    get_db_connection,
    get_post_by_id,
    get_posts,
    get_user_by_id,
)

mysql_bp = Blueprint("mysql", __name__)
logger = get_logger(__name__)


@mysql_bp.route("/debug-mysql")
def debug_mysql():
    """
    Debug route to test MySQL connection.
    Similar to debug_datastore but for Cloud SQL.
    """
    debug_info = {
        "success": False,
        "database_mode": "MySQL/Cloud SQL",
        "connection": {},
        "tables": {},
    }

    try:
        # Test basic connection
        with get_db_connection() as conn:
            from sqlalchemy import text

            result = conn.execute(text("SELECT VERSION()"))
            version = result.fetchone()[0]

            debug_info["connection"] = {
                "status": "connected",
                "mysql_version": version,
            }

            # List all tables
            result = conn.execute(
                text("SHOW TABLES FROM cloned_it")
            )
            tables = [row[0] for row in result.fetchall()]
            debug_info["tables"]["available"] = tables
            debug_info["tables"]["count"] = len(tables)

            # Get sample data from each table
            samples = {}
            for table_name in tables:
                try:
                    result = conn.execute(
                        text(f"SELECT COUNT(*) FROM {table_name}")
                    )
                    count = result.fetchone()[0]

                    result = conn.execute(
                        text(f"SELECT * FROM {table_name} LIMIT 1")
                    )
                    sample_row = result.fetchone()

                    samples[table_name] = {
                        "row_count": count,
                        "sample_row": dict(zip(result.keys(), sample_row))
                        if sample_row
                        else None,
                    }
                except Exception as table_error:
                    samples[table_name] = {"error": str(table_error)}

            debug_info["tables"]["samples"] = samples
            debug_info["success"] = True

    except Exception as e:
        debug_info["error"] = str(e)
        debug_info["error_type"] = type(e).__name__
        logger.error(f"Error in debug_mysql route: {e}", exc_info=True)

    return jsonify(debug_info)


@mysql_bp.route("/posts-mysql")
def posts_mysql():
    """
    Posts page using MySQL instead of Datastore.
    This is the MySQL equivalent of the /posts route.
    """
    try:
        # Get recent posts from MySQL
        posts_data = get_posts(limit=50)

        return render_template("posts.html", posts=posts_data)
    except Exception as e:
        logger.error(f"Error loading posts from MySQL: {e}", exc_info=True)
        return render_template(
            "posts.html",
            posts=[],
            error_message="Error loading posts from MySQL",
        )


@mysql_bp.route("/posts-mysql/submit", methods=["POST"])
@login_required
def submit_post_mysql():
    """
    Handle post submission using MySQL.
    This is the MySQL equivalent of /posts/submit.
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
            posts_data = get_posts(limit=50)
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
            posts_data = get_posts(limit=50)
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

        # Format data for MySQL
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
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

        # Write to MySQL
        post_id = create_post(post_data)

        if post_id:
            logger.info(
                f"Successfully created post with ID: {post_id} by {author_name}"
            )
            posts_data = get_posts(limit=50)
            return render_template(
                "posts.html",
                posts=posts_data,
                success_message=f"Post '{title}' published successfully!",
            )
        else:
            logger.error("Failed to create post in MySQL")
            posts_data = get_posts(limit=50)
            return render_template(
                "posts.html",
                posts=posts_data,
                error_message="Failed to create post",
            )

    except Exception as e:
        logger.error(f"Error submitting post to MySQL: {e}", exc_info=True)
        posts_data = get_posts(limit=50)
        return render_template(
            "posts.html", posts=posts_data, error_message=f"Error: {str(e)}"
        )


@mysql_bp.route("/migrate-datastore-to-mysql")
@login_required
def migrate_datastore_to_mysql():
    """
    Migrate data from Datastore to MySQL.
    WARNING: This should be run with caution and ideally once.
    """
    try:
        from app.utils.datastore_client import get_kind_data

        migration_results = {"success": False, "posts_migrated": 0, "errors": []}

        # Migrate Posts
        logger.info("Starting migration of Posts from Datastore to MySQL")
        posts_data = get_kind_data("Post")

        for post in posts_data:
            try:
                # Convert Datastore post to MySQL format
                mysql_post = {
                    "title": post.get("title", ""),
                    "content": post.get("content", ""),
                    "category": post.get("category", "general"),
                    "author_id": post.get("author_id", "anonymous"),
                    "author_name": post.get("author_name", "Anonymous"),
                    "author_email": post.get("author_email", ""),
                    "upvotes": post.get("upvotes", 0),
                    "downvotes": post.get("downvotes", 0),
                    "comment_count": post.get("comment_count", 0),
                    "created_at": post.get("created_at", datetime.utcnow().isoformat()),
                    "updated_at": post.get("updated_at", datetime.utcnow().isoformat()),
                }

                # Insert into MySQL
                post_id = create_post(mysql_post)
                if post_id:
                    migration_results["posts_migrated"] += 1
                    logger.info(f"Migrated post {post.get('id')} to MySQL ID {post_id}")
                else:
                    error_msg = f"Failed to migrate post {post.get('id')}"
                    migration_results["errors"].append(error_msg)
                    logger.error(error_msg)

            except Exception as post_error:
                error_msg = f"Error migrating post {post.get('id')}: {str(post_error)}"
                migration_results["errors"].append(error_msg)
                logger.error(error_msg)

        migration_results["success"] = True
        logger.info(
            f"Migration complete. Migrated {migration_results['posts_migrated']} posts"
        )

        return jsonify(migration_results)

    except Exception as e:
        logger.error(f"Error during migration: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e), "error_type": type(e).__name__})

