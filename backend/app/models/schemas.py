from enum import Enum
from typing import List, Optional, Any
from pydantic import BaseModel, ConfigDict, field_validator
from datetime import datetime, date
from dateutil import parser

class EmailStatus(str, Enum):
    PRE_ALERT = "pre_alert"
    DRAFT = "draft"
    UNKNOWN = "unknown"

class DocType(str, Enum):
    HBL = "hbl"
    MBL = "mbl"
    UNKNOWN = "unknown"

class ContainerInfo(BaseModel):
    weight: Optional[float] = None
    volume: Optional[float] = None
    number: Optional[str] = None

    @field_validator('weight', 'volume', mode='before')
    @classmethod
    def clean_float(cls, v: Any) -> Optional[float]:
        if v is None:
            return None
        if isinstance(v, (float, int)):
            return float(v)
        if isinstance(v, str):
            # Remove common units and whitespace
            cleaned = v.upper().replace('KGS', '').replace('CBM', '').replace('KG', '').strip()
            if not cleaned:
                return None
            try:
                return float(cleaned)
            except ValueError:
                return None
        return v

class DocumentExtraction(BaseModel):
    doc_type: DocType
    bl_number: Optional[str] = None
    email_status: EmailStatus = EmailStatus.UNKNOWN
    raw_text_excerpt: Optional[str] = None
    extraction_confidence: Optional[float] = None

    # Parties
    shipper_name: Optional[str] = None
    consignee_name: Optional[str] = None
    notify_party_name: Optional[str] = None
    carrier_name: Optional[str] = None
    containers: List[ContainerInfo] = []

    # Routing
    port_of_loading: Optional[str] = None
    port_of_discharge: Optional[str] = None
    place_of_receipt: Optional[str] = None
    place_of_delivery: Optional[str] = None

    # Dates
    etd: Optional[datetime] = None
    eta: Optional[datetime] = None

    @field_validator('shipper_name', 'consignee_name', 'notify_party_name', mode='before')
    @classmethod
    def clean_name(cls, v: Any) -> Optional[str]:
        if not v:
            return None
        if isinstance(v, str):
            return v.split(',')[0].strip()
        return v

    @field_validator('etd', 'eta', mode='before')
    @classmethod
    def parse_date(cls, v: Any) -> Optional[datetime]:
        if v is None:
            return None
        if isinstance(v, datetime):
            return v
        if isinstance(v, date):
            return datetime.combine(v, datetime.min.time())
        if isinstance(v, str):
            if not v.strip():
                return None
            try:
                # Use dateutil parser for flexible date parsing
                dt = parser.parse(v)
                return dt
            except (ValueError, TypeError) as e:
                return None
        return v

class ExtractionResult(DocumentExtraction):
    # Metadata
    source_email_id: str
    source_subject: str
    source_from: str
    source_received_at: datetime
    attachment_filename: str
    page_range: List[int]
    created_at: datetime = datetime.now()
    dedupe_key: str

    model_config = ConfigDict(from_attributes=True)

class ProcessingSummary(BaseModel):
    emails_processed: int
    attachments_processed: int
    docs_created: int
    skipped_duplicates: int
    errors: int

class PaginatedResponse(BaseModel):
    """Response model for paginated endpoints."""
    items: List[dict]
    next_cursor: Optional[str] = None
    has_more: bool = False

class LogLevel(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"

class DashboardStats(BaseModel):
    hbl_count: int
    mbl_count: int
    total_docs: int

class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class JobRecord(BaseModel):
    id: str
    status: JobStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    summary: ProcessingSummary
    logs: List[dict] = []
    error_details: List[dict] = []

class IncidentSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class Incident(BaseModel):
    id: str = None
    severity: IncidentSeverity
    message: str
    job_id: Optional[str] = None
    email_id: Optional[str] = None
    timestamp: datetime
    traceback: Optional[str] = None

