import pytest
import time
from app.services.firestore_service import get_db, upsert_document
from google.cloud import firestore

@pytest.mark.anyio
async def test_firestore_write_read():
    """
    Integration test for Firestore.
    Verifies that we can write a document and read it back.
    """
    db = get_db()
    test_collection = "test_connection"
    test_id = f"pytest_{int(time.time())}"
    test_data = {
        "name": "Pytest Integration",
        "timestamp": firestore.SERVER_TIMESTAMP,
        "status": "active"
    }

    # 1. Write document
    await upsert_document(test_collection, test_id, test_data)

    # 2. Read document to verify
    doc_ref = db.collection(test_collection).document(test_id)
    doc = doc_ref.get()

    assert doc.exists
    data = doc.to_dict()
    assert data["name"] == "Pytest Integration"
    assert data["status"] == "active"

    # 3. Cleanup
    doc_ref.delete()

    # 4. Verify deletion
    assert not doc_ref.get().exists
