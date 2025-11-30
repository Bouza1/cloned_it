"""Cloud Function to get posts from Cloud SQL.

This function connects directly to Cloud SQL to retrieve posts data.
Uses the shared db_client module for database connectivity.
"""

from shared.constants import ERROR, ERROR_TYPE, MESSAGE, STATUS, SUCCESS
from constants import ASC, AUTHOR_ID, COMMENT_COUNT, COUNT, CREATED_AT, DESC, DOWNVOTES, ID, LIMIT, OFFSET, CATEGORY, ORDER, ORDER_BY, POSTS, TITLE, TOTAL_COUNT, UPDATED_AT, UPVOTES
import functions_framework
from shared import db_client


@functions_framework.http
def get_posts(request):
    """
    HTTP Cloud Function to get posts from the posts table.
    
    Args:
        request (flask.Request): HTTP request object.
        
    Query Parameters:
        limit: Optional. Maximum number of posts to return (default: 20)
        offset: Optional. Number of posts to skip for pagination (default: 0)
        category: Optional. Filter by category
        author_id: Optional. Filter by author ID
        order_by: Optional. Sort by field (default: created_at)
        order: Optional. Sort direction: 'asc' or 'desc' (default: desc)
    
    Returns:
        JSON response with posts data
    """
    try:
        # Parse query parameters
        request_args = request.args
        limit = int(request_args.get(LIMIT, 20))
        offset = int(request_args.get(OFFSET, 0))
        category = request_args.get(CATEGORY)
        author_id = request_args.get(AUTHOR_ID)
        order_by = request_args.get(ORDER_BY, CREATED_AT)
        order = request_args.get(ORDER, DESC).upper()
        
        # Validate parameters
        if order not in [ASC.upper(), DESC.upper()]:
            order = DESC.upper()
        
        # Allowed order_by fields for security
        allowed_order_fields = [ID, CREATED_AT, UPDATED_AT, UPVOTES, DOWNVOTES, COMMENT_COUNT, TITLE]
        if order_by not in allowed_order_fields:
            order_by = CREATED_AT
        
        # Build query with filters
        query_parts = ["SELECT * FROM posts WHERE 1=1"]
        params = {}
        
        if category:
            query_parts.append("AND category = :category")
            params[CATEGORY] = category
        
        if author_id:
            query_parts.append("AND author_id = :author_id")
            params[AUTHOR_ID] = author_id
        
        query_parts.append(f"ORDER BY {order_by} {order}")
        query_parts.append("LIMIT :limit OFFSET :offset")
        params[LIMIT] = limit
        params[OFFSET] = offset
        
        query = " ".join(query_parts)
        
        # Execute query using shared db_client
        posts = db_client.execute_query(query, params)
        
        # Convert datetime objects to ISO format strings
        for post in posts:
            for key, value in post.items():
                if hasattr(value, "isoformat"):
                    post[key] = value.isoformat()
        
        # Get total count for pagination
        count_query = "SELECT COUNT(*) as total FROM posts WHERE 1=1"
        count_params = {}
        
        if category:
            count_query += " AND category = :category"
            count_params[CATEGORY] = category
        
        if author_id:
            count_query += " AND author_id = :author_id"
            count_params[AUTHOR_ID] = author_id
        
        total_result = db_client.execute_query(count_query, count_params)
        total_count = total_result[0]["total"] if total_result else 0
        
        response = {
            STATUS: SUCCESS,
            TOTAL_COUNT: total_count,
            COUNT: len(posts),
            LIMIT: limit,
            OFFSET: offset,
            POSTS: posts,
        }
        
        return response, 200
        
    except Exception as e:
        error_response = {
            STATUS: ERROR,
            MESSAGE: str(e),
            ERROR_TYPE: type(e).__name__,
        }
        print(f"Error in get_posts: {e}")
        return error_response, 500

