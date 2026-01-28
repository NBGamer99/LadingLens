from fastapi import APIRouter, HTTPException, Query, Path, BackgroundTasks, Depends
from typing import Optional, List
import uuid
import traceback
from datetime import datetime

from app.models.schemas import (
    ProcessingSummary, PaginatedResponse,
    DashboardStats, JobStatus, LogLevel
)
from app.services import firestore_service, processing_service
from pydantic import BaseModel

router = APIRouter()
class JobListResponse(BaseModel):
    """Response for the jobs list endpoint."""
    jobs: List[dict]

class ProcessResponse(BaseModel):
    """Response from the /process endpoint including job tracking."""
    job_id: str
    summary: ProcessingSummary = None
class IncidentListResponse(BaseModel):
    items: List[dict]
class DocumentQueryParams:
    """Common query parameters for document retrieval."""
    def __init__(
        self,
        limit: int = Query(4, ge=1, le=100),
        cursor: Optional[str] = Query(None),
        carrier: Optional[str] = Query(None, description="Filter by carrier name"),
        pol: Optional[str] = Query(None, description="Filter by Port of Loading"),
        pod: Optional[str] = Query(None, description="Filter by Port of Discharge")
    ):
        self.limit = limit
        self.cursor = cursor
        self.filters = {
            "carrier": carrier,
            "pol": pol,
            "pod": pod
        }
        # Remove None values
        self.filters = {k: v for k, v in self.filters.items() if v is not None}

@router.post("/process", response_model=ProcessResponse)
async def process_emails_endpoint(
    background_tasks: BackgroundTasks,
    skip_dedupe: bool = Query(False, description="Skip deduplication for testing pagination")
):
    """
    Trigger email processing in the background.
    Returns immediately with a Job ID.
    """
    # Generate unique job ID
    job_id = f"job_{uuid.uuid4().hex[:12]}"

    # Create job record in Firestore
    try:
        await firestore_service.create_job(job_id)
        await firestore_service.update_job_status(job_id, JobStatus.RUNNING.value)
        await firestore_service.append_job_log(job_id, LogLevel.INFO.value, "Job started")
    except Exception as e:
        print(f"⚠️  Could not create job record: {e}")
        raise HTTPException(status_code=500, detail="Failed to initialize job tracking")

    # Define the background task wrapper
    async def run_processing_task(jid: str, dedup: bool):
        try:
            summary = await processing_service.process_emails(jid, dedup)

            # Update job status to completed
            # FAILED only if errors occurred AND nothing useful happened (no docs created, no duplicates skipped)
            final_status = JobStatus.FAILED.value if summary.errors > 0 and summary.docs_created == 0 and summary.skipped_duplicates == 0 else JobStatus.COMPLETED.value

            await firestore_service.append_job_log(
                jid, LogLevel.INFO.value,
                f"Job completed: {summary.docs_created} docs created, {summary.errors} errors"
            )
            await firestore_service.update_job_status(
                jid,
                final_status,
                summary=summary.model_dump(),
                completed_at=datetime.now().isoformat()
            )

        except Exception as e:
            print(f"❌ Critical job failure: {e}")
            await firestore_service.append_job_log(
                jid, LogLevel.ERROR.value,
                f"Critical failure: {str(e)}"
            )
            await firestore_service.append_job_error(
                jid,
                error=str(e),
                traceback_str=traceback.format_exc()
            )
            await firestore_service.update_job_status(
                jid, JobStatus.FAILED.value,
                completed_at=datetime.now().isoformat()
            )

    # Run in background
    background_tasks.add_task(run_processing_task, job_id, skip_dedupe)

    return ProcessResponse(job_id=job_id)


@router.get("/hbl", response_model=PaginatedResponse)
async def get_hbl(params: DocumentQueryParams = Depends()):
    """
    Get HBL documents with cursor-based pagination and optional filters.
    """
    result = await firestore_service.get_documents("hbl", params.limit, params.cursor, params.filters)
    return PaginatedResponse(**result)

@router.get("/mbl", response_model=PaginatedResponse)
async def get_mbl(params: DocumentQueryParams = Depends()):
    """
    Get MBL documents with cursor-based pagination and optional filters.
    """
    result = await firestore_service.get_documents("mbl", params.limit, params.cursor, params.filters)
    return PaginatedResponse(**result)

@router.get("/stats", response_model=DashboardStats)
async def get_stats():
    """
    Get dashboard statistics (document counts).
    """
    hbl_count = await firestore_service.get_document_count("hbl")
    mbl_count = await firestore_service.get_document_count("mbl")

    return DashboardStats(
        hbl_count=hbl_count,
        mbl_count=mbl_count,
        total_docs=hbl_count + mbl_count
    )

@router.get("/jobs", response_model=JobListResponse)
async def get_jobs(limit: int = Query(10, ge=1, le=50)):
    """
    Get recent processing jobs.
    """
    jobs = await firestore_service.get_recent_jobs(limit)
    return JobListResponse(jobs=jobs)


@router.get("/jobs/{job_id}")
async def get_job(job_id: str = Path(..., description="Job ID to retrieve")):
    """
    Get detailed information about a specific job.
    """
    job = await firestore_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return job

@router.get("/incidents", response_model=IncidentListResponse)
async def get_incidents(limit: int = Query(10, ge=1, le=50)):
    """
    Get recent incidents (errors aggregated from processing jobs).
    """
    incidents = await firestore_service.get_recent_job_errors(limit)
    return IncidentListResponse(items=incidents)

class FilterOptionsResponse(BaseModel):
    """Available filter options from existing data."""
    carriers: List[str]
    pols: List[str]
    pods: List[str]

@router.get("/filter-options", response_model=FilterOptionsResponse)
async def get_filter_options():
    """
    Get available filter options (distinct values from existing documents).
    """
    options = await firestore_service.get_filter_options()
    return FilterOptionsResponse(**options)
