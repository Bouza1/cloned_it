"""
Cloud Function to delete old posts from Cloud SQL.

This function contains the actual SQL DELETE query.
It uses the shared db_client module for generic database operations.

This is an example of a scheduled/maintenance function that can be
triggered by Cloud Scheduler to perform periodic cleanup.
"""

import functions_framework
import sys
import os

# Add parent directory to path to import shared module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shared import db_client


@functions_framework.http
def cleanup_old_posts(request):
    """
    HTTP Cloud Function to delete posts older than a certain date.
    
    This function contains the actual SQL query and business logic.
    The shared module only provides generic database utilities.
    
    This can be triggered by Cloud Scheduler to run periodically.
    
    Query Parameters:
        days_old: Number of days (default: 365)
        dry_run: If "true", only count without deleting (default: false)
    
    Returns:
        JSON response with deletion results
    """
    try:
        # Parse query parameters
        request_args = request.args
        days_old = int(request_args.get("days_old", 365))
        dry_run = request_args.get("dry_run", "false").lower() == "true"
        
        # Validate days_old
        if days_old < 30:
            return {
                "status": "error",
                "message": "days_old must be at least 30 to prevent accidental deletion"
            }, 400
        
        # =========================================
        # This function writes its own SQL query
        # =========================================
        
        # First, count how many posts would be deleted
        count_query = f"""
        SELECT COUNT(*) as count
        FROM posts
        WHERE created_at < DATE_SUB(NOW(), INTERVAL {days_old} DAY)
        """
        
        result = db_client.execute_query(count_query)
        count = result[0]['count'] if result else 0
        
        if dry_run:
            return {
                "status": "success",
                "dry_run": True,
                "posts_to_delete": count,
                "days_old": days_old,
                "message": f"Would delete {count} posts older than {days_old} days"
            }, 200
        
        # Actually delete the posts
        if count > 0:
            delete_query = f"""
            DELETE FROM posts
            WHERE created_at < DATE_SUB(NOW(), INTERVAL {days_old} DAY)
            """
            
            # Use generic execute_update from shared module
            deleted_count = db_client.execute_update(delete_query)
            
            print(f"Deleted {deleted_count} posts older than {days_old} days")
            
            return {
                "status": "success",
                "deleted_count": deleted_count,
                "days_old": days_old,
                "message": f"Successfully deleted {deleted_count} posts"
            }, 200
        else:
            return {
                "status": "success",
                "deleted_count": 0,
                "days_old": days_old,
                "message": "No posts to delete"
            }, 200
        
    except ValueError as e:
        return {
            "status": "error",
            "message": f"Invalid parameter: {str(e)}"
        }, 400
        
    except Exception as e:
        print(f"Error in cleanup_old_posts: {e}")
        return {
            "status": "error",
            "message": str(e),
            "error_type": type(e).__name__
        }, 500

