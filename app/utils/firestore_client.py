"""Simple Firestore client for reading data."""

from google.cloud import firestore

from app.utils.logging.logger import get_logger

logger = get_logger(__name__)

# Lazy initialization - only create client when needed
_db = None


def _get_db():
    """Get or create Firestore client instance."""
    global _db
    if _db is None:
        # On App Engine, this will automatically use the default credentials
        _db = firestore.Client()
    return _db


def get_collection_data(collection_name: str) -> list[dict]:
    """
    Read all documents from a Firestore collection.

    Args:
        collection_name: Name of the collection to read from

    Returns:
        List of dictionaries containing document data
    """
    try:
        db = _get_db()
        docs = db.collection(collection_name).stream()
        data = []
        for doc in docs:
            doc_data = doc.to_dict()
            doc_data["id"] = doc.id  # Include document ID
            data.append(doc_data)

        logger.info(
            f"Successfully retrieved {len(data)} documents from {collection_name}"
        )
        return data
    except Exception as e:
        logger.error(
            f"Error reading from Firestore collection {collection_name}: {e}"
        )
        return []


def get_document(collection_name: str, document_id: str) -> dict | None:
    """
    Read a single document from Firestore.

    Args:
        collection_name: Name of the collection
        document_id: ID of the document to retrieve

    Returns:
        Dictionary containing document data, or None if not found
    """
    try:
        db = _get_db()
        doc_ref = db.collection(collection_name).document(document_id)
        doc = doc_ref.get()

        if doc.exists:
            data = doc.to_dict()
            data["id"] = doc.id
            logger.info(
                f"Successfully retrieved document {document_id} from {collection_name}"
            )
            return data
        else:
            logger.warning(
                f"Document {document_id} not found in {collection_name}"
            )
            return None
    except Exception as e:
        logger.error(
            f"Error reading document {document_id} from {collection_name}: {e}"
        )
        return None
