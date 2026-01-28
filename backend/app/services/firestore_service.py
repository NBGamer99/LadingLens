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

JOBS_COLLECTION = settings.FIRESTORE_COLLECTION_JOBS


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

async def get_document_count(collection_name: str) -> int:
    """
    Get the total count of documents in a collection.
    Uses Firestore aggregation for efficient counting without fetching documents.
    """
    database = get_db()
    collection_ref = database.collection(collection_name)

    # Use aggregation query for efficient count
    count_query = collection_ref.count()
    results = count_query.get()

    # Results is a list of AggregationResult objects
    for result in results:
        return result[0].value

    return 0

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



async def create_job(job_id: str) -> Dict[str, Any]:
    """
    Create a new job record with 'pending' status.
    Returns the created job data.
    """
    from datetime import datetime
    from app.models.schemas import JobStatus

    database = get_db()
    job_data = {
        "id": job_id,
        "status": JobStatus.PENDING.value,
        "started_at": datetime.now().isoformat(),
        "completed_at": None,
        "summary": {
            "emails_processed": 0,
            "attachments_processed": 0,
            "docs_created": 0,
            "skipped_duplicates": 0,
            "errors": 0
        },
        "logs": [],
        "error_details": []
    }

    doc_ref = database.collection(JOBS_COLLECTION).document(job_id)
    doc_ref.set(job_data)
    return job_data


async def update_job_status(
    job_id: str,
    status: str,
    summary: Optional[Dict[str, Any]] = None,
    completed_at: Optional[str] = None
) -> None:
    """
    Update job status and optionally the summary.
    """
    database = get_db()
    doc_ref = database.collection(JOBS_COLLECTION).document(job_id)

    update_data: Dict[str, Any] = {"status": status}

    if summary:
        update_data["summary"] = summary

    if completed_at:
        update_data["completed_at"] = completed_at

    doc_ref.update(update_data)


async def append_job_log(
    job_id: str,
    level: str,
    message: str,
    email_id: Optional[str] = None,
    attachment: Optional[str] = None
) -> None:
    """
    Append a log entry to a job.
    Uses array union to avoid race conditions.
    """
    from datetime import datetime

    database = get_db()
    doc_ref = database.collection(JOBS_COLLECTION).document(job_id)

    log_entry = {
        "level": level,
        "message": message,
        "timestamp": datetime.now().isoformat(),
    }

    if email_id:
        log_entry["email_id"] = email_id
    if attachment:
        log_entry["attachment"] = attachment

    doc_ref.update({
        "logs": firestore.ArrayUnion([log_entry])
    })


async def append_job_error(
    job_id: str,
    error: str,
    email_id: Optional[str] = None,
    attachment: Optional[str] = None,
    traceback_str: Optional[str] = None
) -> None:
    """
    Append an error detail to a job.
    """
    from datetime import datetime

    database = get_db()
    doc_ref = database.collection(JOBS_COLLECTION).document(job_id)

    error_detail = {
        "error": error,
        "timestamp": datetime.now().isoformat(),
    }

    if email_id:
        error_detail["email_id"] = email_id
    if attachment:
        error_detail["attachment"] = attachment
    if traceback_str:
        error_detail["traceback"] = traceback_str

    doc_ref.update({
        "error_details": firestore.ArrayUnion([error_detail])
    })


async def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch a single job by ID.
    Returns None if not found.
    """
    database = get_db()
    doc_ref = database.collection(JOBS_COLLECTION).document(job_id)
    doc = doc_ref.get()

    if doc.exists:
        return doc.to_dict()
    return None


async def get_recent_jobs(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Fetch the most recent jobs, ordered by started_at descending.
    """
    database = get_db()
    query = database.collection(JOBS_COLLECTION).order_by(
        "started_at",
        direction=firestore.Query.DESCENDING
    ).limit(limit)

    docs = list(query.stream())
    return [doc.to_dict() for doc in docs]


async def get_recent_job_errors(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Aggregate recent errors from job records.
    Traverses recent jobs and collects their error_details.
    """
    # Fetch more jobs than the limit to ensure we find enough errors
    # (assuming not every job has errors)
    jobs = await get_recent_jobs(limit=limit * 2)

    incidents = []

    for job in jobs:
        if not job.get("error_details"):
            continue

        for idx, error in enumerate(job["error_details"]):
            # Normalize to Incident schema structure
            incidents.append({
                "id": f"{job['id']}_{idx}",
                "severity": "high", # Default severity
                "message": error.get("error", "Unknown error"),
                "job_id": job['id'],
                "email_id": error.get("email_id"),
                "timestamp": error.get("timestamp", job.get("started_at")),
                "traceback": error.get("traceback")
            })

            if len(incidents) >= limit:
                break

        if len(incidents) >= limit:
            break

    return incidents
