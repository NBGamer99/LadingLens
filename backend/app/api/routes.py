from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
import hashlib
from datetime import datetime

from app.models.schemas import ExtractionResult, ProcessingSummary, EmailStatus
from app.services import gmail_service, pdf_service, extraction_service, firestore_service
from app.config import settings

router = APIRouter()

def generate_dedupe_key(email_id: str, filename: str, page_num: int) -> str:
    return hashlib.md5(f"{email_id}_{filename}_{page_num}".encode()).hexdigest()

@router.post("/process", response_model=ProcessingSummary)
async def process_emails():
    # 1. Fetch recent emails
    emails = gmail_service.fetch_recent_emails(limit=10)

    summary = ProcessingSummary(
        emails_processed=0,
        attachments_processed=0,
        docs_created=0,
        skipped_duplicates=0,
        errors=0
    )

    for email_data in emails:
        summary.emails_processed += 1
        try:
            body, attachments, metadata = gmail_service.parse_email_message(email_data)
            email_status = gmail_service.classify_email_status(body)

            for att in attachments:
                summary.attachments_processed += 1
                try:
                    # 3. Process PDF
                    file_bytes = att['data']
                    pages = pdf_service.extract_text_from_pdf(file_bytes)
                    # TODO: Implement logic to group pages into single documents
                    for page in pages:
                        text = page['text']
                        if not text.strip():
                            continue

                        dedupe_key = generate_dedupe_key(metadata['source_email_id'], att['filename'], page['page_num'])
                        # TODO: Check for duplicates
                except Exception as e:
                    print(f"Error processing attachment {att['filename']}: {e}")
                    summary.errors += 1

        except Exception as e:
            print(f"Error processing email {email_data.get('id')}: {e}")
            summary.errors += 1

    return summary

@router.get("/hbl", response_model=List[dict])
async def get_hbl(limit: int = 20):
    return await firestore_service.get_documents(settings.FIRESTORE_COLLECTION_HBL, limit)

@router.get("/mbl", response_model=List[dict])
async def get_mbl(limit: int = 20):
    return await firestore_service.get_documents(settings.FIRESTORE_COLLECTION_MBL, limit)
