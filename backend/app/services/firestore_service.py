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

async def get_documents(collection_name: str, limit: int = 20, cursor: Optional[str] = None) -> List[Dict[str, Any]]:
    database = get_db()
    query = database.collection(collection_name).order_by("created_at", direction=firestore.Query.DESCENDING).limit(limit)

    if cursor:
        # For simplicity in this demo, we assume cursor is a document ID
        # In a real app, you might use a timestamp or a more robust cursor
        cursor_doc = database.collection(collection_name).document(cursor).get()
        if cursor_doc.exists:
            query = query.start_after(cursor_doc)

    docs = query.stream()
    return [d.to_dict() for d in docs]
