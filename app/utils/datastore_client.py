"""Datastore client for reading data."""

from google.cloud import datastore

from app.utils.logging.logger import get_logger

logger = get_logger(__name__)

# Lazy initialization - only create client when needed
_db = None


def _get_db():
    """Get or create Datastore client instance."""
    global _db
    if _db is None:
        try:
            _db = datastore.Client()
            logger.info(
                f"Datastore client initialized for project: {_db.project} (using default database)"
            )
        except Exception as e:
            logger.error(
                f"Failed to initialize Datastore client: {e}", exc_info=True
            )
            raise
    return _db


def get_kind_data(kind_name: str, limit: int = None) -> list[dict]:
    """
    Read all entities from a Datastore kind.

    Args:
        kind_name: Name of the kind to read from
        limit: Optional limit on number of entities to retrieve

    Returns:
        List of dictionaries containing entity data
    """
    try:
        logger.info(f"Attempting to read from kind: {kind_name}")
        db = _get_db()

        # Create a query for the kind
        query = db.query(kind=kind_name)

        if limit:
            query = query.fetch(limit=limit)
        else:
            query = query.fetch()

        data = []
        entity_count = 0

        for entity in query:
            entity_count += 1
            # Convert entity to dict and include the key
            entity_dict = dict(entity)
            entity_dict["id"] = entity.key.id or entity.key.name
            entity_dict["key"] = entity.key.path
            data.append(entity_dict)

            # Log first entity as sample
            if entity_count == 1:
                logger.debug(
                    f"First entity ID: {entity.key.id or entity.key.name}, keys: {list(entity_dict.keys())}"
                )

        if entity_count == 0:
            logger.warning(
                f"Kind '{kind_name}' returned 0 entities. "
                f"Possible issues: wrong kind name, no data, or permission issues."
            )
        else:
            logger.info(
                f"Successfully retrieved {len(data)} entities from {kind_name}"
            )
        return data
    except Exception as e:
        logger.error(
            f"Error reading from Datastore kind {kind_name}: {e}",
            exc_info=True,
        )
        return []


def get_entity(
    kind_name: str, entity_id: str = None, entity_name: str = None
) -> dict | None:
    """
    Read a single entity from Datastore.

    Args:
        kind_name: Name of the kind
        entity_id: Numeric ID of the entity
        entity_name: String name of the entity

    Returns:
        Dictionary containing entity data, or None if not found
    """
    try:
        db = _get_db()

        # Create the key
        if entity_id:
            key = db.key(kind_name, int(entity_id))
        elif entity_name:
            key = db.key(kind_name, entity_name)
        else:
            logger.error("Either entity_id or entity_name must be provided")
            return None

        entity = db.get(key)

        if entity:
            data = dict(entity)
            data["id"] = entity.key.id or entity.key.name
            data["key"] = entity.key.path
            logger.info(
                f"Successfully retrieved entity {entity_id or entity_name} from {kind_name}"
            )
            return data
        else:
            logger.warning(
                f"Entity {entity_id or entity_name} not found in {kind_name}"
            )
            return None
    except Exception as e:
        logger.error(
            f"Error reading entity {entity_id or entity_name} from {kind_name}: {e}",
            exc_info=True,
        )
        return None


def list_kinds() -> list[str]:
    """
    List all kinds in the Datastore database.

    Returns:
        List of kind names
    """
    try:
        db = _get_db()
        query = db.query(kind="__kind__")
        query.keys_only()

        kinds = [entity.key.id_or_name for entity in query.fetch()]

        # Log all kinds including system ones for debugging
        logger.debug(f"All kinds (including system): {kinds}")

        # Filter out system kinds (those starting with __)
        user_kinds = [k for k in kinds if not k.startswith("__")]

        if not user_kinds:
            logger.warning("No user kinds found")
            return []

        logger.info(f"Found {len(user_kinds)} user kinds: {user_kinds}")
        return user_kinds
    except Exception as e:
        logger.error(f"Error listing kinds: {e}", exc_info=True)
        return []


def create_entity(
    kind_name: str, data: dict, entity_id: str = None, entity_name: str = None
) -> dict | None:
    """
    Create a new entity in Datastore.

    Args:
        kind_name: Name of the kind to write to
        data: Dictionary containing the entity data
        entity_id: Optional numeric ID for the entity
        entity_name: Optional string name for the entity
                    If neither ID nor name provided, Datastore will auto-generate an ID

    Returns:
        Dictionary containing the created entity data with its key, or None if failed
    """
    try:
        db = _get_db()

        # Create the key
        if entity_id:
            key = db.key(kind_name, int(entity_id))
        elif entity_name:
            key = db.key(kind_name, entity_name)
        else:
            # Auto-generate ID
            key = db.key(kind_name)

        # Create entity with the key
        entity = datastore.Entity(key=key)
        entity.update(data)

        # Save to Datastore
        db.put(entity)

        # Return the created entity with its key info
        result = dict(entity)
        result["id"] = entity.key.id or entity.key.name
        result["key"] = entity.key.path

        logger.info(
            f"Successfully created entity in {kind_name} with ID: {result['id']}"
        )
        return result
    except Exception as e:
        logger.error(
            f"Error creating entity in {kind_name}: {e}", exc_info=True
        )
        return None


def update_entity(
    kind_name: str,
    entity_id: str = None,
    entity_name: str = None,
    data: dict = None,
) -> dict | None:
    """
    Update an existing entity in Datastore.

    Args:
        kind_name: Name of the kind
        entity_id: Numeric ID of the entity
        entity_name: String name of the entity
        data: Dictionary containing the fields to update

    Returns:
        Dictionary containing the updated entity data, or None if failed
    """
    try:
        db = _get_db()

        # Create the key
        if entity_id:
            key = db.key(kind_name, int(entity_id))
        elif entity_name:
            key = db.key(kind_name, entity_name)
        else:
            logger.error("Either entity_id or entity_name must be provided")
            return None

        # Get existing entity
        entity = db.get(key)

        if not entity:
            logger.warning(
                f"Entity {entity_id or entity_name} not found in {kind_name}"
            )
            return None

        # Update the entity
        entity.update(data)
        db.put(entity)

        # Return updated entity
        result = dict(entity)
        result["id"] = entity.key.id or entity.key.name
        result["key"] = entity.key.path

        logger.info(
            f"Successfully updated entity {entity_id or entity_name} in {kind_name}"
        )
        return result
    except Exception as e:
        logger.error(
            f"Error updating entity {entity_id or entity_name} in {kind_name}: {e}",
            exc_info=True,
        )
        return None


def delete_entity(
    kind_name: str, entity_id: str = None, entity_name: str = None
) -> bool:
    """
    Delete an entity from Datastore.

    Args:
        kind_name: Name of the kind
        entity_id: Numeric ID of the entity
        entity_name: String name of the entity

    Returns:
        True if successful, False otherwise
    """
    try:
        db = _get_db()

        # Create the key
        if entity_id:
            key = db.key(kind_name, int(entity_id))
        elif entity_name:
            key = db.key(kind_name, entity_name)
        else:
            logger.error("Either entity_id or entity_name must be provided")
            return False

        # Delete the entity
        db.delete(key)

        logger.info(
            f"Successfully deleted entity {entity_id or entity_name} from {kind_name}"
        )
        return True
    except Exception as e:
        logger.error(
            f"Error deleting entity {entity_id or entity_name} from {kind_name}: {e}",
            exc_info=True,
        )
        return False
