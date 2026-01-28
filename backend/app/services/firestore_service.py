from google.cloud import firestore
from google.cloud.firestore import Client
from typing import List, Dict, Any, Optional
import os

from app.config import settings

# Initialize Firestore Client
# In local dev with a service account file, it picks up GOOGLE_APPLICATION_CREDENTIALS
# or we can pass it explicitly.
# For this assignment, we assume the credentials.json or default auth is set up.

db: Optional[Client] = None

def get_db() -> Client:
    global db
    if db is None:
        # If we had a specific service account path in settings, we'd use it.
        # Otherwise, relies on standard Google auth.
        try:
           db = firestore.Client(project=settings.PROJECT_ID)
        except Exception as e:
            print(f"Warning: Could not init Firestore: {e}")
            # For local testing without real GCP, we might need a mock or just fail.
            raise e
    return db

async def upsert_document(collection_name: str, document_id: str, data: Dict[str, Any]):
    database = get_db()
    doc_ref = database.collection(collection_name).document(document_id)
    doc_ref.set(data)

async def document_exists(collection_name: str, document_id: str) -> bool:
    """Check if a document already exists in a collection."""
    database = get_db()
    doc_ref = database.collection(collection_name).document(document_id)
    doc = doc_ref.get()
    return doc.exists

async def get_documents(collection_name: str, limit: int = 4, cursor: Optional[str] = None) -> Dict[str, Any]:
    """
    Fetch documents with cursor-based pagination.
    Returns: { items: [...], next_cursor: str | None, has_more: bool }
    """
    database = get_db()
    # Request one extra to determine if there are more results
    query = database.collection(collection_name).order_by("created_at", direction=firestore.Query.DESCENDING).limit(limit + 1)

    if cursor:
        # Cursor is a document ID (dedupe_key)
        cursor_doc = database.collection(collection_name).document(cursor).get()
        if cursor_doc.exists:
            query = query.start_after(cursor_doc)

    docs = list(query.stream())

    # Check if there are more results
    has_more = len(docs) > limit
    if has_more:
        docs = docs[:limit]  # Trim to requested limit

    items = []
    last_doc_id = None
    for d in docs:
        doc_dict = d.to_dict()
        doc_dict['id'] = d.id  # Include document ID for cursor
        items.append(doc_dict)
        last_doc_id = d.id

    return {
        "items": items,
        "next_cursor": last_doc_id if has_more else None,
        "has_more": has_more
    }
