"""Cloud Function to get MySQL/Cloud SQL statistics and data.

This function connects directly to Cloud SQL to retrieve database statistics
and sample data, demonstrating how Cloud Functions can access Cloud SQL.

Uses the shared db_client module for database connectivity.
"""

import functions_framework
from shared import db_client


@functions_framework.http
def get_mysql_stats(request):
    """
    HTTP Cloud Function to get MySQL/Cloud SQL statistics.
    
    This function demonstrates how a Cloud Function can directly connect
    to Cloud SQL to retrieve database information and statistics.
    
    Args:
        request (flask.Request): HTTP request object.
        
    Query Parameters:
        table: Optional. Specific table name to get detailed info about
        limit: Optional. Limit for sample rows (default: 5)
    
    Returns:
        JSON response with MySQL database statistics
    """
    try:
        # Parse query parameters
        request_args = request.args
        specific_table = request_args.get("table", None)
        limit = int(request_args.get("limit", 5))
        
        # Connect to database using shared module
        with db_client.get_db_connection() as conn:
            from sqlalchemy import text
            # Get MySQL version
            result = conn.execute(text("SELECT VERSION()"))
            mysql_version = result.fetchone()[0]
            
            # Get database name
            result = conn.execute(text("SELECT DATABASE()"))
            database_name = result.fetchone()[0]
            
            # Get all tables in the database
            result = conn.execute(text(f"SHOW TABLES FROM {database_name}"))
            tables = [row[0] for row in result.fetchall()]
            
            # Build response
            response = {
                "status": "success",
                "database": database_name,
                "mysql_version": mysql_version,
                "total_tables": len(tables),
                "tables": tables,
            }
            
            # Get detailed info for each table (or specific table if requested)
            tables_to_check = [specific_table] if specific_table else tables
            table_details = {}
            
            for table_name in tables_to_check:
                try:
                    # Get row count
                    result = conn.execute(text(f"SELECT COUNT(*) FROM `{table_name}`"))
                    row_count = result.fetchone()[0]
                    
                    # Get table structure
                    result = conn.execute(text(f"DESCRIBE `{table_name}`"))
                    columns = []
                    for row in result.fetchall():
                        columns.append({
                            "field": row[0],
                            "type": row[1],
                            "null": row[2],
                            "key": row[3],
                            "default": str(row[4]) if row[4] is not None else None,
                            "extra": row[5],
                        })
                    
                    # Get sample rows
                    result = conn.execute(text(f"SELECT * FROM `{table_name}` LIMIT {limit}"))
                    sample_rows = []
                    for row in result.fetchall():
                        row_dict = {}
                        for idx, col_name in enumerate(result.keys()):
                            # Convert datetime and other non-JSON-serializable types to string
                            value = row[idx]
                            if hasattr(value, "isoformat"):
                                value = value.isoformat()
                            row_dict[col_name] = value
                        sample_rows.append(row_dict)
                    
                    table_details[table_name] = {
                        "row_count": row_count,
                        "columns": columns,
                        "sample_rows": sample_rows,
                    }
                    
                except Exception as table_error:
                    table_details[table_name] = {
                        "error": str(table_error),
                        "error_type": type(table_error).__name__,
                    }
            
            response["table_details"] = table_details
            
        return response, 200
        
    except Exception as e:
        error_response = {
            "status": "error",
            "message": str(e),
            "error_type": type(e).__name__,
        }
        print(f"Error in get_mysql_stats: {e}")
        return error_response, 500

