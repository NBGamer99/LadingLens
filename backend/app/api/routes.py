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
    """
    Process the 10 most recent emails from Gmail.
    Classifies each email as pre_alert or draft based on body content.
    For now, just logs results to terminal - no Firestore storage.
    """
    print("\n" + "=" * 60)
    print("🚀 STARTING EMAIL PROCESSING")
    print("=" * 60)

    # 1. Fetch recent emails
    try:
        emails = gmail_service.fetch_recent_emails(limit=10)
        print(f"📧 Fetched {len(emails)} emails from Gmail")
    except Exception as e:
        print(f"❌ Failed to fetch emails: {e}")
        return ProcessingSummary(
            emails_processed=0,
            attachments_processed=0,
            docs_created=0,
            skipped_duplicates=0,
            errors=1
        )

    summary = ProcessingSummary(
        emails_processed=0,
        attachments_processed=0,
        docs_created=0,
        skipped_duplicates=0,
        errors=0
    )

    for idx, email_data in enumerate(emails):
        summary.emails_processed += 1
        print(f"\n{'─' * 50}")
        print(f"📩 Email {idx + 1}/{len(emails)}")

        try:
            body, attachments, metadata = gmail_service.parse_email_message(email_data)
            email_status = gmail_service.classify_email_status(body)

            # Log email details
            thread_id = email_data.get('threadId', 'N/A')
            print(f"   ID:      {metadata['source_email_id']}")
            print(f"   Thread:  {thread_id[:16]}...")
            print(f"   From:    {metadata['source_from']}")
            print(f"   Subject: {metadata['source_subject']}")
            print(f"   Status:  {email_status.value.upper()}")
            print(f"   PDFs:    {len(attachments)} attachment(s)")

            # Log body snippet for debugging classification
            body_preview = body[:150].replace('\n', ' ').strip()
            if body_preview:
                print(f"   Body:    \"{body_preview}...\"")

            # Filter: Only process if Pre-alert or Draft
            if email_status == EmailStatus.UNKNOWN:
                print(f"   ⏭️  Skipping - not a pre-alert or draft")
                continue

            print(f"   ✅ MATCHED - Processing as {email_status.value}")

            # List attachments
            for att in attachments:
                summary.attachments_processed += 1
                print(f"\n   📎 Attachment: {att['filename']}")

                try:
                    # Fetch PDF content
                    file_bytes = gmail_service.fetch_attachment_blob(metadata['source_email_id'], att)
                    if not file_bytes:
                        print(f"      ⚠️  Could not fetch content")
                        continue

                    print(f"      📄 Size: {len(file_bytes)} bytes")

                    # Extract pages
                    pages = pdf_service.extract_text_from_pdf(file_bytes)
                    print(f"      📑 Pages: {len(pages)}")

                    # Classify document type for each page
                    for page in pages:
                        text = page['text']
                        if not text.strip():
                            print(f"      Page {page['page_num']}: (empty)")
                            continue

                        doc_type = pdf_service.classify_doc_type_from_text(text)
                        text_preview = text[:80].replace('\n', ' ').strip()
                        print(f"      Page {page['page_num']}: {doc_type.value.upper()} - \"{text_preview}...\"")

                        # Generate dedupe key (for future use)
                        dedupe_key = generate_dedupe_key(metadata['source_email_id'], att['filename'], page['page_num'])

                        # Count as created (even though we're not storing yet)
                        if doc_type.value != "unknown":
                            summary.docs_created += 1

                except Exception as e:
                    print(f"      ❌ Error: {e}")
                    summary.errors += 1

        except Exception as e:
            print(f"   ❌ Error processing email: {e}")
            summary.errors += 1

    # Final summary
    print(f"\n{'=' * 60}")
    print("📊 PROCESSING COMPLETE")
    print(f"   Emails processed:    {summary.emails_processed}")
    print(f"   Attachments scanned: {summary.attachments_processed}")
    print(f"   Documents found:     {summary.docs_created}")
    print(f"   Errors:              {summary.errors}")
    print(f"{'=' * 60}\n")

    return summary

@router.get("/hbl", response_model=List[dict])
async def get_hbl(limit: int = 20):
    return await firestore_service.get_documents(settings.FIRESTORE_COLLECTION_HBL, limit)

@router.get("/mbl", response_model=List[dict])
async def get_mbl(limit: int = 20):
    return await firestore_service.get_documents(settings.FIRESTORE_COLLECTION_MBL, limit)
