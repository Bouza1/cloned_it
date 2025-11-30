"""
Shared database client for Cloud Functions.

This module provides GENERIC database utilities that can be imported
by any Cloud Function. Individual functions contain their own SQL queries
and business logic.

Generic utilities provided:
- get_db_connection(): Context manager for database connections
- execute_query(): Execute SELECT queries and return results
- execute_update(): Execute INSERT/UPDATE/DELETE queries
- _get_secret(): Retrieve secrets from Secret Manager
"""

import os
from contextlib import contextmanager
from typing import Any, Dict, List, Optional

import sqlalchemy
from google.cloud import secretmanager
from google.cloud.sql.connector import Connector
from sqlalchemy import text
from sqlalchemy.pool import NullPool


# Global variables for connection reuse across invocations
_engine = None
_connector = None


def _get_secret(secret_id: str) -> str:
    """
    Get secret from Secret Manager.
    
    Args:
        secret_id: ID of the secret to retrieve
        
    Returns:
        Secret value as string
    """
    try:
        project_id = os.environ.get("GCP_PROJECT")
        if not project_id:
            raise ValueError("GCP_PROJECT environment variable not set")
        
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
        response = client.access_secret_version(request={"name": name})
        
        return response.payload.data.decode("UTF-8")
    except Exception as e:
        print(f"Error getting secret {secret_id}: {e}")
        return os.environ.get("DB_PASSWORD", "")


def _get_db_engine():
    """Get or create SQLAlchemy engine for Cloud SQL."""
    global _engine, _connector
    
    if _engine is None:
        try:
            db_user = os.environ.get("DB_USER", "root")
            db_name = os.environ.get("DB_NAME", "cloned_it")
            instance_connection_name = os.environ.get("CLOUD_SQL_CONNECTION_NAME")
            
            if not instance_connection_name:
                raise ValueError("CLOUD_SQL_CONNECTION_NAME environment variable not set")
            
            db_password = _get_secret("db-password")
            
            _connector = Connector()
            
            def getconn():
                return _connector.connect(
                    instance_connection_name,
                    "pymysql",
                    user=db_user,
                    password=db_password,
                    db=db_name,
                )
            
            _engine = sqlalchemy.create_engine(
                "mysql+pymysql://",
                creator=getconn,
                poolclass=NullPool,
            )
            
            print(f"MySQL engine initialized for database: {db_name}")
            
            with _engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                print("Database connection test successful")
                
        except Exception as e:
            print(f"Failed to initialize MySQL engine: {e}")
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
    Generic function to execute SELECT queries.
    
    Individual Cloud Functions write their own SQL queries and pass them here.
    
    Args:
        query: SQL SELECT query string
        params: Dictionary of parameters for the query (use :param_name in query)
        
    Returns:
        List of dictionaries containing query results
        
    Example:
        results = execute_query(
            "SELECT * FROM posts WHERE category = :cat LIMIT :limit",
            {"cat": "tech", "limit": 10}
        )
    """
    try:
        with get_db_connection() as conn:
            result = conn.execute(text(query), params or {})
            rows = [dict(zip(result.keys(), row)) for row in result.fetchall()]
            print(f"Query executed, returned {len(rows)} rows")
            return rows
            
    except Exception as e:
        print(f"Error executing query: {e}")
        raise


def execute_update(query: str, params: Dict[str, Any] = None) -> int:
    """
    Generic function to execute INSERT, UPDATE, or DELETE queries.
    
    Individual Cloud Functions write their own SQL queries and pass them here.
    
    Args:
        query: SQL INSERT/UPDATE/DELETE query string
        params: Dictionary of parameters for the query (use :param_name in query)
        
    Returns:
        Number of rows affected
        
    Example:
        affected = execute_update(
            "INSERT INTO posts (title, content) VALUES (:title, :content)",
            {"title": "My Post", "content": "Content here"}
        )
    """
    try:
        with get_db_connection() as conn:
            result = conn.execute(text(query), params or {})
            conn.commit()
            affected = result.rowcount
            print(f"Update executed, {affected} rows affected")
            return affected
            
    except Exception as e:
        print(f"Error executing update: {e}")
        raise


def execute_insert(query: str, params: Dict[str, Any] = None) -> Optional[int]:
    """
    Generic function to execute INSERT queries and return the inserted ID.
    
    Individual Cloud Functions write their own SQL queries and pass them here.
    
    Args:
        query: SQL INSERT query string
        params: Dictionary of parameters for the query (use :param_name in query)
        
    Returns:
        ID of the inserted row (lastrowid), or None if failed
        
    Example:
        post_id = execute_insert(
            "INSERT INTO posts (title, content) VALUES (:title, :content)",
            {"title": "My Post", "content": "Content here"}
        )
    """
    try:
        with get_db_connection() as conn:
            result = conn.execute(text(query), params or {})
            conn.commit()
            inserted_id = result.lastrowid
            print(f"Insert executed, ID: {inserted_id}")
            return inserted_id
            
    except Exception as e:
        print(f"Error executing insert: {e}")
        raise


def close_connection():
    """Close the database connection pool."""
    global _engine, _connector
    
    if _engine:
        _engine.dispose()
        _engine = None
        print("Database engine disposed")
    
    if _connector:
        _connector.close()
        _connector = None
        print("Cloud SQL connector closed")

