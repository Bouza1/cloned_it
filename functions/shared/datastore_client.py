"""
Shared Datastore client for Cloud Functions.

This module provides GENERIC Datastore utilities that can be imported
by any Cloud Function. Individual functions contain their own queries
and business logic.

"""

from typing import Any, Dict, List, Optional, Tuple
from google.cloud import datastore


# Global variable for client reuse across invocations
_client = None


def get_datastore_client() -> datastore.Client:
    """
    Get or create Datastore client.
    
    Returns:
        Datastore client instance
    """
    global _client
    
    if _client is None:
        _client = datastore.Client()
        print(f"Datastore client initialized for project: {_client.project}")
    
    return _client


def get_all_kinds(include_system_kinds: bool = False) -> List[str]:
    """
    Get all entity kinds in Datastore.
    
    Args:
        include_system_kinds: Whether to include system kinds (those starting with __)
        
    Returns:
        List of kind names
    """
    try:
        client = get_datastore_client()
        query = client.query(kind="__kind__")
        query.keys_only()
        
        all_kinds = [entity.key.id_or_name for entity in query.fetch()]
        
        if not include_system_kinds:
            all_kinds = [k for k in all_kinds if not k.startswith("__")]
        
        print(f"Found {len(all_kinds)} kinds")
        return all_kinds
        
    except Exception as e:
        print(f"Error getting kinds: {e}")
        raise


def count_entities(kind: str, filters: List[Tuple[str, str, Any]] = None) -> int:
    """
    Count entities of a specific kind with optional filters.
    
    Args:
        kind: The entity kind to count
        filters: Optional list of filters as (property, operator, value) tuples
                Example: [("status", "=", "active"), ("age", ">", 18)]
        
    Returns:
        Number of entities
        
    Example:
        count = count_entities("User", [("active", "=", True)])
    """
    try:
        client = get_datastore_client()
        query = client.query(kind=kind)
        query.keys_only()
        
        if filters:
            for prop, operator, value in filters:
                query.add_filter(prop, operator, value)
        
        count = len(list(query.fetch()))
        print(f"Counted {count} entities of kind '{kind}'")
        return count
        
    except Exception as e:
        print(f"Error counting entities: {e}")
        raise


def query_entities(
    kind: str,
    filters: List[Tuple[str, str, Any]] = None,
    order: List[str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    keys_only: bool = False
) -> List[datastore.Entity]:
    """
    Query entities with filters, ordering, and pagination.
    
    Args:
        kind: The entity kind to query
        filters: Optional list of filters as (property, operator, value) tuples
        order: Optional list of properties to order by (prefix with '-' for descending)
        limit: Maximum number of entities to return
        offset: Number of entities to skip
        keys_only: If True, only return entity keys (faster)
        
    Returns:
        List of entities or keys
        
    Example:
        users = query_entities(
            "User",
            filters=[("status", "=", "active")],
            order=["-created_at"],
            limit=10
        )
    """
    try:
        client = get_datastore_client()
        query = client.query(kind=kind)
        
        if keys_only:
            query.keys_only()
        
        if filters:
            for prop, operator, value in filters:
                query.add_filter(prop, operator, value)
        
        if order:
            query.order = order
        
        # Fetch with limit and offset
        iterator = query.fetch(limit=limit, offset=offset)
        entities = list(iterator)
        
        print(f"Queried {len(entities)} entities of kind '{kind}'")
        return entities
        
    except Exception as e:
        print(f"Error querying entities: {e}")
        raise


def get_entity(kind: str, entity_id: Any) -> Optional[datastore.Entity]:
    """
    Get a single entity by its key.
    
    Args:
        kind: The entity kind
        entity_id: The entity ID (can be string name or integer ID)
        
    Returns:
        Entity if found, None otherwise
        
    Example:
        user = get_entity("User", "user123")
        post = get_entity("Post", 12345)
    """
    try:
        client = get_datastore_client()
        key = client.key(kind, entity_id)
        entity = client.get(key)
        
        if entity:
            print(f"Retrieved entity: {kind}/{entity_id}")
        else:
            print(f"Entity not found: {kind}/{entity_id}")
        
        return entity
        
    except Exception as e:
        print(f"Error getting entity: {e}")
        raise


def entities_to_dict(entities: List[datastore.Entity]) -> List[Dict[str, Any]]:
    """
    Convert Datastore entities to dictionaries for JSON serialization.
    
    Args:
        entities: List of Datastore entities
        
    Returns:
        List of dictionaries
    """
    result = []
    for entity in entities:
        entity_dict = dict(entity)
        
        # Add key information
        entity_dict["_key"] = {
            "kind": entity.key.kind,
            "id": entity.key.id,
            "name": entity.key.name,
        }
        
        # Convert datetime objects to ISO format strings
        for key, value in entity_dict.items():
            if hasattr(value, "isoformat"):
                entity_dict[key] = value.isoformat()
        
        result.append(entity_dict)
    
    return result


def put_entity(kind: str, entity_id: Any = None, properties: Dict[str, Any] = None) -> datastore.Key:
    """
    Create or update an entity.
    
    Args:
        kind: The entity kind
        entity_id: Optional entity ID (string name or integer ID). If None, auto-generates ID
        properties: Dictionary of properties to set on the entity
        
    Returns:
        The entity key
        
    Example:
        key = put_entity("User", "user123", {"name": "John", "email": "john@example.com"})
        key = put_entity("Post", properties={"title": "My Post"})  # Auto-generated ID
    """
    try:
        client = get_datastore_client()
        
        if entity_id:
            key = client.key(kind, entity_id)
        else:
            key = client.key(kind)
        
        entity = datastore.Entity(key=key)
        
        if properties:
            entity.update(properties)
        
        client.put(entity)
        print(f"Saved entity: {kind}/{entity.key.id or entity.key.name}")
        
        return entity.key
        
    except Exception as e:
        print(f"Error putting entity: {e}")
        raise


def delete_entity(kind: str, entity_id: Any) -> None:
    """
    Delete a single entity by its key.
    
    Args:
        kind: The entity kind
        entity_id: The entity ID (string name or integer ID)
        
    Example:
        delete_entity("User", "user123")
    """
    try:
        client = get_datastore_client()
        key = client.key(kind, entity_id)
        client.delete(key)
        print(f"Deleted entity: {kind}/{entity_id}")
        
    except Exception as e:
        print(f"Error deleting entity: {e}")
        raise


def delete_entities(keys: List[datastore.Key], batch_size: int = 500) -> int:
    """
    Delete multiple entities in batches.
    
    Args:
        keys: List of entity keys to delete
        batch_size: Number of entities to delete per batch (Datastore limit is 500)
        
    Returns:
        Number of entities deleted
        
    Example:
        keys = [client.key("Session", sid) for sid in old_session_ids]
        deleted = delete_entities(keys)
    """
    try:
        client = get_datastore_client()
        total_deleted = 0
        
        # Process in batches
        for i in range(0, len(keys), batch_size):
            batch = keys[i:i + batch_size]
            client.delete_multi(batch)
            total_deleted += len(batch)
            print(f"Deleted batch: {len(batch)} entities")
        
        print(f"Total deleted: {total_deleted} entities")
        return total_deleted
        
    except Exception as e:
        print(f"Error deleting entities: {e}")
        raise


# ============================================================================
# Utility Functions
# ============================================================================

def get_kind_stats() -> Dict[str, int]:
    """
    Get count of entities for each kind.
    
    Returns:
        Dictionary mapping kind names to entity counts
        
    Example:
        stats = get_kind_stats()
        # {"User": 150, "Post": 523, "Comment": 1240}
    """
    try:
        kinds = get_all_kinds()
        stats = {}
        
        for kind_name in kinds:
            stats[kind_name] = count_entities(kind_name)
        
        return stats
        
    except Exception as e:
        print(f"Error getting kind stats: {e}")
        raise

