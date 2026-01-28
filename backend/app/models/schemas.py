from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from datetime import datetime

class EmailStatus(str, Enum):
    PRE_ALERT = "pre_alert"
    DRAFT = "draft"
    UNKNOWN = "unknown"

class DocType(str, Enum):
    HBL = "hbl"
    MBL = "mbl"
    UNKNOWN = "unknown"

class ContainerInfo(BaseModel):
    weight: Optional[str] = None
    volume: Optional[str] = None
    number: Optional[str] = None

class DocumentExtraction(BaseModel):
    doc_type: DocType
    bl_number: Optional[str] = None
    email_status: EmailStatus = EmailStatus.UNKNOWN
    containers: List[ContainerInfo] = []

    # Parties
    shipper_name: Optional[str] = None
    consignee_name: Optional[str] = None
    notify_party_name: Optional[str] = None
    carrier_name: Optional[str] = None

    # Routing
    port_of_loading: Optional[str] = None
    port_of_discharge: Optional[str] = None
    place_of_receipt: Optional[str] = None
    place_of_delivery: Optional[str] = None

    # Dates
    etd: Optional[str] = None
    eta: Optional[str] = None

    extraction_confidence: Optional[float] = None
    raw_text_excerpt: Optional[str] = None

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

