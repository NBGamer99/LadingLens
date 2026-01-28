import hashlib
import uuid
import traceback
from datetime import datetime
from typing import List, Optional

from app.models.schemas import (
    ProcessingSummary, EmailStatus, LogLevel, JobStatus, ExtractionResult
)
from app.services import gmail_service, pdf_service, extraction_service, firestore_service
from app.services.pdf_service import PDFExtractionError
from app.services.gmail_service import GmailAuthError
from app.config import settings

class ProcessingError(Exception):
    """Base exception for processing errors."""
    pass

def generate_dedupe_key(email_id: str, filename: str, page_num: int) -> str:
    return hashlib.md5(f"{email_id}_{filename}_{page_num}".encode()).hexdigest()

async def process_emails(job_id: str, skip_dedupe: bool = False) -> ProcessingSummary:
    """
    Core business logic for processing emails.
    Orchestrates: Gmail fetch -> PDF Extract -> AI Extraction -> Firestore Store.
    Updates the job status and logs in real-time.
    """

    print("\n" + "=" * 60)
    print(f"🚀 STARTING EMAIL PROCESSING (Job: {job_id})")
    if skip_dedupe:
        print("⚠️  DEDUPE DISABLED - Testing mode")
    print("=" * 60)

    # Initialize summary
    summary = ProcessingSummary(
        emails_processed=0,
        attachments_processed=0,
        docs_created=0,
        skipped_duplicates=0,
        errors=0
    )

    try:
        # 1. Fetch recent emails
        try:
            emails = gmail_service.fetch_recent_emails(limit=10)
            print(f"📧 Fetched {len(emails)} emails from Gmail")
            await firestore_service.append_job_log(
                job_id, LogLevel.INFO.value,
                f"Fetched {len(emails)} emails from Gmail"
            )
        except Exception as e:
            # Re-raise as a known error to be handled by caller or top-level catch
            raise ProcessingError(f"Failed to fetch emails: {str(e)}")

        # Process each email
        for idx, email_data in enumerate(emails):
            summary.emails_processed += 1
            print(f"\n{'─' * 50}")
            print(f"📩 Email {idx + 1}/{len(emails)}")

            try:
                body, attachments, metadata = gmail_service.parse_email_message(email_data)
                email_status = gmail_service.classify_email_status(body)
                email_id = metadata['source_email_id']

                # Log email details
                thread_id = email_data.get('threadId', 'N/A')
                print(f"   ID:      {email_id}")
                print(f"   Thread:  {thread_id[:16]}...")
                print(f"   From:    {metadata['source_from']}")
                print(f"   Subject: {metadata['source_subject']}")
                print(f"   Status:  {email_status.value.upper()}")
                print(f"   PDFs:    {len(attachments)} attachment(s)")

                # Filter: Only process if Pre-alert or Draft
                if email_status == EmailStatus.UNKNOWN:
                    print(f"   ⏭️  Skipping - not a pre-alert or draft")
                    await firestore_service.append_job_log(
                        job_id, LogLevel.INFO.value,
                        f"Skipping email - not a pre-alert or draft",
                        email_id=email_id
                    )
                    continue

                print(f"   ✅ MATCHED - Processing as {email_status.value}")
                await firestore_service.append_job_log(
                    job_id, LogLevel.INFO.value,
                    f"Processing email as {email_status.value}: {metadata['source_subject'][:50]}",
                    email_id=email_id
                )

                # Process attachments
                for att in attachments:
                    summary.attachments_processed += 1
                    filename = att['filename']
                    print(f"\n   📎 Attachment: {filename}")

                    try:
                        # Fetch PDF content
                        file_bytes = gmail_service.fetch_attachment_blob(email_id, att)
                        if not file_bytes:
                            print(f"      ⚠️  Could not fetch content")
                            await firestore_service.append_job_log(
                                job_id, LogLevel.WARNING.value,
                                f"Could not fetch attachment content",
                                email_id=email_id, attachment=filename
                            )
                            continue

                        print(f"      📄 Size: {len(file_bytes)} bytes")

                        # Extract pages
                        try:
                            pages = pdf_service.extract_text_from_pdf(file_bytes)
                        except PDFExtractionError as pdf_err:
                            print(f"      ❌ {pdf_err}")
                            summary.errors += 1
                            await firestore_service.append_job_log(
                                job_id, LogLevel.ERROR.value,
                                f"PDF extraction failed: {str(pdf_err)}",
                                email_id=email_id, attachment=filename
                            )
                            await firestore_service.append_job_error(
                                job_id,
                                error=f"PDF extraction failed: {str(pdf_err)}",
                                email_id=email_id,
                                attachment=filename,
                                traceback_str=traceback.format_exc()
                            )
                            continue  # Skip to next attachment

                        print(f"      📑 Pages: {len(pages)}")
                        await firestore_service.append_job_log(
                            job_id, LogLevel.INFO.value,
                            f"Extracted {len(pages)} pages from PDF",
                            email_id=email_id, attachment=filename
                        )

                        # Classify and Extract for each page (or group)
                        for page in pages:
                            text = page['text']
                            if len(text.strip()) < 100:
                                continue

                            # Generate dedupe key
                            dedupe_key = generate_dedupe_key(email_id, filename, page['page_num'])

                            # Add random suffix for testing if skip_dedupe is enabled
                            if skip_dedupe:
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
                                    source_email_id=email_id,
                                    source_subject=metadata['source_subject'],
                                    source_from=metadata['source_from'],
                                    source_received_at=metadata['source_received_at'],
                                    attachment_filename=filename,
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
                                    await firestore_service.append_job_log(
                                        job_id, LogLevel.INFO.value,
                                        f"Created {result.doc_type.value.upper()} document: {result.bl_number}",
                                        email_id=email_id, attachment=filename
                                    )
                                else:
                                    print(f"      Page {page['page_num']}: ⚠️  Could not identify document type")
                                    await firestore_service.append_job_log(
                                        job_id, LogLevel.WARNING.value,
                                        f"Could not identify document type on page {page['page_num']}",
                                        email_id=email_id, attachment=filename
                                    )

                            except Exception as e:
                                print(f"      Page {page['page_num']}: ❌ Extraction error: {e}")
                                summary.errors += 1
                                await firestore_service.append_job_log(
                                    job_id, LogLevel.ERROR.value,
                                    f"Extraction error on page {page['page_num']}: {str(e)}",
                                    email_id=email_id, attachment=filename
                                )
                                await firestore_service.append_job_error(
                                    job_id,
                                    error=f"Extraction error: {str(e)}",
                                    email_id=email_id,
                                    attachment=filename,
                                    traceback_str=traceback.format_exc()
                                )

                    except Exception as e:
                        print(f"      ❌ Error processing attachment: {e}")
                        summary.errors += 1
                        await firestore_service.append_job_log(
                            job_id, LogLevel.ERROR.value,
                            f"Error processing attachment: {str(e)}",
                            email_id=email_id, attachment=filename
                        )
                        await firestore_service.append_job_error(
                            job_id,
                            error=f"Attachment processing error: {str(e)}",
                            email_id=email_id,
                            attachment=filename,
                            traceback_str=traceback.format_exc()
                        )

            except Exception as e:
                print(f"   ❌ Error processing email: {e}")
                summary.errors += 1
                email_id = email_data.get('id', 'unknown')
                await firestore_service.append_job_log(
                    job_id, LogLevel.ERROR.value,
                    f"Error processing email: {str(e)}",
                    email_id=email_id
                )
                await firestore_service.append_job_error(
                    job_id,
                    error=f"Email processing error: {str(e)}",
                    email_id=email_id,
                    traceback_str=traceback.format_exc()
                )

    except ProcessingError as e:
        # Top level processing errors (like auth failure)
        await firestore_service.append_job_log(
            job_id, LogLevel.ERROR.value,
            str(e)
        )
        await firestore_service.append_job_error(
             job_id,
             error=str(e),
             traceback_str=traceback.format_exc()
        )
        # We don't re-raise here because we want to return the partial summary
        # But we will mark job as failed in the caller or here?
        # Let's let the caller handle the final status update based on summary/exceptions

    return summary
