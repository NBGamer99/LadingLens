from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from typing import List, Optional, AsyncGenerator
import hashlib
import json
from datetime import datetime

from app.models.schemas import ExtractionResult, ProcessingSummary, EmailStatus, PaginatedResponse
from app.services import gmail_service, pdf_service, extraction_service, firestore_service
from app.config import settings

router = APIRouter()

def generate_dedupe_key(email_id: str, filename: str, page_num: int) -> str:
    return hashlib.md5(f"{email_id}_{filename}_{page_num}".encode()).hexdigest()

@router.post("/process", response_model=ProcessingSummary)
async def process_emails(skip_dedupe: bool = Query(False, description="Skip deduplication for testing pagination")):
    """
    Process the 10 most recent emails from Gmail.
    Classifies each email as pre_alert or draft based on body content.

    Args:
        skip_dedupe: If True, skips duplicate checking and creates new records each time (for testing)
    """
    print("\n" + "=" * 60)
    print("🚀 STARTING EMAIL PROCESSING")
    if skip_dedupe:
        print("⚠️  DEDUPE DISABLED - Testing mode")
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

                    # Classify and Extract for each page (or group)
                    # For simplicity, we treat each page as a potential document if it has enough text
                    for page in pages:
                        text = page['text']
                        if len(text.strip()) < 100:
                            continue

                        # Generate dedupe key
                        dedupe_key = generate_dedupe_key(metadata['source_email_id'], att['filename'], page['page_num'])

                        # Add random suffix for testing if skip_dedupe is enabled
                        if skip_dedupe:
                            import uuid
                            dedupe_key = f"{dedupe_key}_{uuid.uuid4().hex[:8]}"

                        # Check if already processed (skip this check if testing)
                        if not skip_dedupe:
                            is_hbl = await firestore_service.document_exists(settings.FIRESTORE_COLLECTION_HBL, dedupe_key)
                            is_mbl = await firestore_service.document_exists(settings.FIRESTORE_COLLECTION_MBL, dedupe_key)

                            if is_hbl or is_mbl:
                                print(f"      Page {page['page_num']}: ⏭️  Skipping (Already in Firestore)")
                                summary.skipped_duplicates += 1
                                continue

                        print(f"      Page {page['page_num']}: 🤖 Extracting with AI...")
                        try:
                            extraction = await extraction_service.extract_data_from_text(text)
                            # Override email_status from our heuristic if it's UNKNOWN
                            if extraction.email_status == EmailStatus.UNKNOWN:
                                extraction.email_status = email_status

                            # Create full result with metadata
                            result = ExtractionResult(
                                **extraction.model_dump(),
                                source_email_id=metadata['source_email_id'],
                                source_subject=metadata['source_subject'],
                                source_from=metadata['source_from'],
                                source_received_at=metadata['source_received_at'],
                                attachment_filename=att['filename'],
                                page_range=[page['page_num']],
                                dedupe_key=dedupe_key,
                                created_at=datetime.now()
                            )

                            # Determine collection
                            collection = settings.FIRESTORE_COLLECTION_HBL if result.doc_type == "hbl" else settings.FIRESTORE_COLLECTION_MBL

                            if result.doc_type != "unknown":
                                await firestore_service.upsert_document(collection, dedupe_key, result.model_dump())
                                print(f"      Page {page['page_num']}: ✅ Saved as {result.doc_type.value.upper()} ({result.bl_number})")
                                summary.docs_created += 1
                            else:
                                print(f"      Page {page['page_num']}: ⚠️  Could not identify document type")

                        except Exception as e:
                            print(f"      Page {page['page_num']}: ❌ Extraction error: {e}")
                            summary.errors += 1

                except Exception as e:
                    print(f"      ❌ Error processing attachment: {e}")
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
    print(f"   Skipped (Dedupe):    {summary.skipped_duplicates}")
    print(f"   Errors:              {summary.errors}")
    print(f"{'=' * 60}\n")

    return summary

@router.get("/process-stream")
async def process_emails_stream(skip_dedupe: bool = Query(False)):
    """
    Stream processing results in real-time using Server-Sent Events.
    Each extracted document is sent as it's processed.
    """
    async def event_generator() -> AsyncGenerator[str, None]:
        summary = {"emails_processed": 0, "attachments_processed": 0, "docs_created": 0, "skipped_duplicates": 0, "errors": 0}

        try:
            emails = gmail_service.fetch_recent_emails(limit=10)
            yield f"data: {json.dumps({'type': 'status', 'message': f'Fetched {len(emails)} emails'})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
            yield f"data: {json.dumps({'type': 'complete', 'summary': summary})}\n\n"
            return

        for idx, email_data in enumerate(emails):
            summary["emails_processed"] += 1

            try:
                body, attachments, metadata = gmail_service.parse_email_message(email_data)
                email_status = gmail_service.classify_email_status(body)

                subject_preview = metadata["source_subject"][:50] if metadata.get("source_subject") else "No subject"
                yield f"data: {json.dumps({'type': 'status', 'message': f'Processing email {idx+1}/{len(emails)}: {subject_preview}...'})}\n\n"

                if email_status == EmailStatus.UNKNOWN:
                    continue

                for att in attachments:
                    summary["attachments_processed"] += 1

                    try:
                        file_bytes = gmail_service.fetch_attachment_blob(metadata['source_email_id'], att)
                        if not file_bytes:
                            continue

                        pages = pdf_service.extract_text_from_pdf(file_bytes)

                        for page in pages:
                            text = page['text']
                            if len(text.strip()) < 100:
                                continue

                            dedupe_key = generate_dedupe_key(metadata['source_email_id'], att['filename'], page['page_num'])

                            if skip_dedupe:
                                import uuid
                                dedupe_key = f"{dedupe_key}_{uuid.uuid4().hex[:8]}"

                            if not skip_dedupe:
                                is_hbl = await firestore_service.document_exists(settings.FIRESTORE_COLLECTION_HBL, dedupe_key)
                                is_mbl = await firestore_service.document_exists(settings.FIRESTORE_COLLECTION_MBL, dedupe_key)
                                if is_hbl or is_mbl:
                                    summary["skipped_duplicates"] += 1
                                    continue

                            try:
                                extraction = await extraction_service.extract_data_from_text(text)
                                if extraction.email_status == EmailStatus.UNKNOWN:
                                    extraction.email_status = email_status

                                result = ExtractionResult(
                                    **extraction.model_dump(),
                                    source_email_id=metadata['source_email_id'],
                                    source_subject=metadata['source_subject'],
                                    source_from=metadata['source_from'],
                                    source_received_at=metadata['source_received_at'],
                                    attachment_filename=att['filename'],
                                    page_range=[page['page_num']],
                                    dedupe_key=dedupe_key,
                                    created_at=datetime.now()
                                )

                                collection = settings.FIRESTORE_COLLECTION_HBL if result.doc_type == "hbl" else settings.FIRESTORE_COLLECTION_MBL

                                if result.doc_type != "unknown":
                                    await firestore_service.upsert_document(collection, dedupe_key, result.model_dump())
                                    summary["docs_created"] += 1

                                    # Stream the newly created document
                                    result_dict = result.model_dump()
                                    result_dict['created_at'] = result_dict['created_at'].isoformat() if result_dict.get('created_at') else None
                                    result_dict['source_received_at'] = str(result_dict.get('source_received_at', ''))
                                    yield f"data: {json.dumps({'type': 'document', 'data': result_dict})}\n\n"

                            except Exception as e:
                                summary["errors"] += 1
                                yield f"data: {json.dumps({'type': 'error', 'message': f'Extraction error: {str(e)}'})}\n\n"

                    except Exception as e:
                        summary["errors"] += 1

            except Exception as e:
                summary["errors"] += 1

        yield f"data: {json.dumps({'type': 'complete', 'summary': summary})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )

@router.get("/hbl", response_model=PaginatedResponse)
async def get_hbl(limit: int = Query(4, ge=1, le=100), cursor: Optional[str] = Query(None)):
    """
    Get HBL documents with cursor-based pagination.
    - limit: Number of items per page (1-100, default 4)
    - cursor: Document ID to start after (from previous response's next_cursor)
    """
    result = await firestore_service.get_documents(settings.FIRESTORE_COLLECTION_HBL, limit, cursor)
    return PaginatedResponse(**result)

@router.get("/mbl", response_model=PaginatedResponse)
async def get_mbl(limit: int = Query(4, ge=1, le=100), cursor: Optional[str] = Query(None)):
    """
    Get MBL documents with cursor-based pagination.
    - limit: Number of items per page (1-100, default 4)
    - cursor: Document ID to start after (from previous response's next_cursor)
    """
    result = await firestore_service.get_documents(settings.FIRESTORE_COLLECTION_MBL, limit, cursor)
    return PaginatedResponse(**result)

