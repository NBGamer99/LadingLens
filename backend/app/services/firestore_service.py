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

async def get_documents(collection_name: str, limit: int = 20, cursor: Optional[str] = None) -> List[Dict[str, Any]]:
    database = get_db()
    query = database.collection(collection_name).limit(limit).order_by("created_at", direction=firestore.Query.DESCENDING)

    # TODO: proper cursor-based pagination.
    # right now just grabbing the latest N.
    # to fix: need to pass the last_doc snapshot or timestamp.

    docs = query.stream()
    return [d.to_dict() for d in docs]
