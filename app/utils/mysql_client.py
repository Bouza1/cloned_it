"""MySQL client for Cloud SQL database operations."""

import os
from contextlib import contextmanager
from typing import Any, Dict, List, Optional

import pymysql
import sqlalchemy
from google.cloud.sql.connector import Connector
from sqlalchemy import text
from sqlalchemy.pool import NullPool

from app.utils.logging.logger import get_logger
from app.utils.secret_manager import get_secret

logger = get_logger(__name__)

# Lazy initialization - only create engine when needed
_engine = None
_connector = None


def _get_db_engine():
    """Get or create SQLAlchemy engine for Cloud SQL."""
    global _engine, _connector
    
    if _engine is None:
        try:
            # Get database configuration
            db_user = os.environ.get("DB_USER", "root")
            db_name = os.environ.get("DB_NAME", "cloned_it")
            instance_connection_name = os.environ.get("CLOUD_SQL_CONNECTION_NAME")
            
            if not instance_connection_name:
                raise ValueError("CLOUD_SQL_CONNECTION_NAME environment variable not set")
            
            # Get password from Secret Manager
            try:
                db_password = get_secret("db-password")
            except Exception as e:
                logger.warning(f"Could not get password from Secret Manager: {e}")
                db_password = os.environ.get("DB_PASSWORD", "")
            
            # Initialize Cloud SQL Python Connector
            _connector = Connector()
            
            def getconn():
                """Create a database connection."""
                conn = _connector.connect(
                    instance_connection_name,
                    "pymysql",
                    user=db_user,
                    password=db_password,
                    db=db_name,
                )
                return conn
            
            # Create SQLAlchemy engine
            _engine = sqlalchemy.create_engine(
                "mysql+pymysql://",
                creator=getconn,
                poolclass=NullPool,  # Use NullPool for App Engine
            )
            
            logger.info(
                f"MySQL engine initialized for database: {db_name} "
                f"(instance: {instance_connection_name})"
            )
            
            # Test connection
            with _engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                logger.info("Database connection test successful")
                
        except Exception as e:
            logger.error(
                f"Failed to initialize MySQL engine: {e}", exc_info=True
            )
            raise
    
    return _engine


@contextmanager
def get_db_connection():
    """
    Context manager for database connections.
    
    Usage:
        with get_db_connection() as conn:
            result = conn.execute(text("SELECT * FROM users"))
    """
    engine = _get_db_engine()
    conn = engine.connect()
    try:
        yield conn
    finally:
        conn.close()


def execute_query(query: str, params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    """
    Execute a SELECT query and return results as list of dictionaries.
    
    Args:
        query: SQL query string
        params: Dictionary of parameters for the query
        
    Returns:
        List of dictionaries containing query results
    """
    try:
        with get_db_connection() as conn:
            result = conn.execute(text(query), params or {})
            
            # Convert result to list of dicts
            columns = result.keys()
            rows = [dict(zip(columns, row)) for row in result.fetchall()]
            
            logger.info(f"Query executed successfully, returned {len(rows)} rows")
            return rows
            
    except Exception as e:
        logger.error(f"Error executing query: {e}", exc_info=True)
        return []


def execute_update(query: str, params: Dict[str, Any] = None) -> int:
    """
    Execute an INSERT, UPDATE, or DELETE query.
    
    Args:
        query: SQL query string
        params: Dictionary of parameters for the query
        
    Returns:
        Number of rows affected
    """
    try:
        with get_db_connection() as conn:
            result = conn.execute(text(query), params or {})
            conn.commit()
            
            affected_rows = result.rowcount
            logger.info(f"Update executed successfully, {affected_rows} rows affected")
            return affected_rows
            
    except Exception as e:
        logger.error(f"Error executing update: {e}", exc_info=True)
        return 0


def create_post(post_data: Dict[str, Any]) -> Optional[int]:
    """
    Create a new post in the database.
    
    Args:
        post_data: Dictionary containing post data
        
    Returns:
        ID of the created post, or None if failed
    """
    try:
        query = """
        INSERT INTO posts (
            title, content, category, author_id, author_name, author_email,
            upvotes, downvotes, comment_count, created_at, updated_at
        ) VALUES (
            :title, :content, :category, :author_id, :author_name, :author_email,
            :upvotes, :downvotes, :comment_count, :created_at, :updated_at
        )
        """
        
        with get_db_connection() as conn:
            result = conn.execute(text(query), post_data)
            conn.commit()
            post_id = result.lastrowid
            
            logger.info(f"Successfully created post with ID: {post_id}")
            return post_id
            
    except Exception as e:
        logger.error(f"Error creating post: {e}", exc_info=True)
        return None


def get_posts(limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    """
    Get posts from the database.
    
    Args:
        limit: Maximum number of posts to retrieve
        offset: Number of posts to skip
        
    Returns:
        List of dictionaries containing post data
    """
    try:
        query = """
        SELECT 
            id, title, content, category, author_id, author_name, author_email,
            upvotes, downvotes, comment_count, created_at, updated_at
        FROM posts
        ORDER BY created_at DESC
        LIMIT :limit OFFSET :offset
        """
        
        return execute_query(query, {"limit": limit, "offset": offset})
        
    except Exception as e:
        logger.error(f"Error getting posts: {e}", exc_info=True)
        return []


def get_post_by_id(post_id: int) -> Optional[Dict[str, Any]]:
    """
    Get a single post by ID.
    
    Args:
        post_id: ID of the post
        
    Returns:
        Dictionary containing post data, or None if not found
    """
    try:
        query = """
        SELECT 
            id, title, content, category, author_id, author_name, author_email,
            upvotes, downvotes, comment_count, created_at, updated_at
        FROM posts
        WHERE id = :post_id
        """
        
        results = execute_query(query, {"post_id": post_id})
        return results[0] if results else None
        
    except Exception as e:
        logger.error(f"Error getting post {post_id}: {e}", exc_info=True)
        return None


def update_post(post_id: int, update_data: Dict[str, Any]) -> bool:
    """
    Update an existing post.
    
    Args:
        post_id: ID of the post to update
        update_data: Dictionary containing fields to update
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Build UPDATE query dynamically based on provided fields
        set_clause = ", ".join([f"{key} = :{key}" for key in update_data.keys()])
        query = f"UPDATE posts SET {set_clause} WHERE id = :post_id"
        
        update_data["post_id"] = post_id
        affected_rows = execute_update(query, update_data)
        
        return affected_rows > 0
        
    except Exception as e:
        logger.error(f"Error updating post {post_id}: {e}", exc_info=True)
        return False


def delete_post(post_id: int) -> bool:
    """
    Delete a post from the database.
    
    Args:
        post_id: ID of the post to delete
        
    Returns:
        True if successful, False otherwise
    """
    try:
        query = "DELETE FROM posts WHERE id = :post_id"
        affected_rows = execute_update(query, {"post_id": post_id})
        
        return affected_rows > 0
        
    except Exception as e:
        logger.error(f"Error deleting post {post_id}: {e}", exc_info=True)
        return False


def create_user(user_data: Dict[str, Any]) -> bool:
    """
    Create or update a user in the database.
    
    Args:
        user_data: Dictionary containing user data (id, email, name, picture)
        
    Returns:
        True if successful, False otherwise
    """
    try:
        query = """
        INSERT INTO users (id, email, name, picture, created_at, last_login)
        VALUES (:id, :email, :name, :picture, NOW(), NOW())
        ON DUPLICATE KEY UPDATE
            name = :name,
            picture = :picture,
            last_login = NOW()
        """
        
        affected_rows = execute_update(query, user_data)
        logger.info(f"Successfully created/updated user: {user_data.get('email')}")
        return affected_rows > 0
        
    except Exception as e:
        logger.error(f"Error creating/updating user: {e}", exc_info=True)
        return False


def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a user by ID.
    
    Args:
        user_id: ID of the user
        
    Returns:
        Dictionary containing user data, or None if not found
    """
    try:
        query = """
        SELECT id, email, name, picture, created_at, last_login
        FROM users
        WHERE id = :user_id
        """
        
        results = execute_query(query, {"user_id": user_id})
        return results[0] if results else None
        
    except Exception as e:
        logger.error(f"Error getting user {user_id}: {e}", exc_info=True)
        return None


def close_connection():
    """Close the database connection pool."""
    global _engine, _connector
    
    if _engine:
        _engine.dispose()
        _engine = None
        logger.info("Database engine disposed")
    
    if _connector:
        _connector.close()
        _connector = None
        logger.info("Cloud SQL connector closed")

