import os.path
import base64
from typing import List, Tuple, Optional
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.exceptions import RefreshError
import logging

from app.config import settings
from app.models.schemas import EmailStatus

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

logger = logging.getLogger(__name__)


import re


class GmailAuthError(Exception):
    """Custom exception for Gmail authentication errors."""
    pass


def get_gmail_service():
    """
    Get an authenticated Gmail service instance.

    This function expects auth tokens (token.json and credentials.json) to be
    pre-configured and provided with the application. It does NOT initiate
    OAuth flows or prompt users to authenticate.

    Raises:
        GmailAuthError: When authentication fails (missing/invalid token or credentials)
    """
    creds = None

    # Check if token file exists
    if not os.path.exists(settings.gmail_token_path):
        logger.error(f"Token file not found")
        raise GmailAuthError(
            f"Gmail token file not found. "
            "The token.json file should be provided with the application. "
            "Please ensure the secrets/ directory contains a valid token.json file."
        )

    # Load the token
    try:
        creds = Credentials.from_authorized_user_file(settings.gmail_token_path, SCOPES)
    except Exception as e:
        logger.error(f"Failed to load token file: {e}")
        raise GmailAuthError(
            f"Invalid or corrupted token file at '{settings.gmail_token_path}'. "
            f"Error: {str(e)}"
        )

    # Check if token needs refresh
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            try:
                logger.info("Token expired, attempting to refresh...")
                creds.refresh(Request())
                # Save the refreshed token
                try:
                    with open(settings.gmail_token_path, 'w') as token:
                        token.write(creds.to_json())
                    logger.info("Token refreshed and saved successfully")
                except Exception as e:
                    logger.warning(f"Could not save refreshed token: {e}")
            except RefreshError as e:
                logger.error(f"Token refresh failed: {e}")
                raise GmailAuthError(
                    "Gmail token has expired and could not be refreshed. "
                    "The token.json file may need to be regenerated. "
                    f"Error: {str(e)}"
                )
            except Exception as e:
                logger.error(f"Unexpected error refreshing token: {e}")
                raise GmailAuthError(f"Failed to refresh Gmail token: {str(e)}")
        else:
            logger.error("Token is invalid and cannot be refreshed (no refresh token)")
            raise GmailAuthError(
                "Gmail token is invalid and cannot be refreshed. "
                "The token.json file may be incomplete or expired. "
                "Please provide a valid token.json file with a refresh_token."
            )

    # Build and return the service
    try:
        return build('gmail', 'v1', credentials=creds)
    except Exception as e:
        logger.error(f"Failed to build Gmail service: {e}")
        raise GmailAuthError(f"Failed to connect to Gmail API: {str(e)}")

def fetch_recent_emails(limit: int = 10) -> List[dict]:
    """
    Fetches the most recent emails using the threads API.
    Returns only the latest message per thread, which is more efficient
    and matches the intent of getting unique conversations.

    Message: A single, unique email sent or received. Every "Reply" or "Forward" is its own distinct message with its own unique messageId.
    Thread: A collection of messages that belong together (a conversation). Gmail groups messages into threads based on headers like In-Reply-To and References.

    """
    service = get_gmail_service()


    results = service.users().threads().list(userId='me', maxResults=limit).execute()
    threads = results.get('threads', [])

    unique_emails = []

    for thread in threads:
        # Fetch the full thread to get all messages
        full_thread = service.users().threads().get(
            userId='me',
            id=thread['id'],
            format='full'
        ).execute()

        thread_messages = full_thread.get('messages', [])

        if thread_messages:
            thread_messages.sort(
                key=lambda m: int(m.get('internalDate', 0)),
                reverse=True  # Newest first
            )
            unique_emails.append(thread_messages[0])

    logger.info(f"Fetched {len(threads)} threads, returning {len(unique_emails)} latest messages")
    return unique_emails

def get_header(headers: List[dict], name: str) -> str:
    for h in headers:
        if h['name'].lower() == name.lower():
            return h['value']
    return ""

def extract_latest_body(body: str) -> str:
    """
    Extracts the latest message body by removing quoted replies and signatures.
    """
    if not body:
        return ""

    # Common separators for replies/forwards (flexible regex)
    # 1. On ... wrote:
    # 2. -----Original Message-----
    # 3. From: ... Sent: ...
    # 4. Sent from my ... (Signature)

    on_wrote_pattern = r'On\s+.*wrote:[\s\S]*'

    original_msg_pattern = r'-+\s*Original Message\s*-+[\s\S]*'

    from_header_pattern = r'\n\s*From:.*[\r\n]+\s*(?:Sent|Date):.*[\s\S]*'

    sent_from_pattern = r'\n\s*Sent from my.*'

    cleaned = body

    simple_splitters = [
        "-----Original Message-----",
        "----- Original Message -----",
        "---------- Forwarded message ---------",
        "---------- Forwarded message ----------"
    ]
    for s in simple_splitters:
        if s in cleaned:
            cleaned = cleaned.split(s)[0]

    # Regex cleaning
    cleaned = re.sub(on_wrote_pattern, '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(original_msg_pattern, '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(from_header_pattern, '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(sent_from_pattern, '', cleaned, flags=re.IGNORECASE)

    return cleaned.strip()


def parse_email_message(message: dict) -> Tuple[str, List[dict], dict]:
    """
    Parses the email to get body and attachment METADATA (not content).
    Returns: (newest_body, attachment_summaries, metadata)
    """
    payload = message.get('payload', {})
    headers = payload.get('headers', [])

    metadata = {
        "source_email_id": message['id'],
        "source_subject": get_header(headers, "Subject"),
        "source_from": get_header(headers, "From"),
        "source_received_at": message.get('internalDate')
    }

    body = ""
    attachments = []

    parts = [payload]
    while parts:
        part = parts.pop(0)
        if part.get('parts'):
            parts.extend(part['parts'])

        # Extract Body
        if part.get('mimeType') == 'text/plain' and 'data' in part.get('body', {}):
             data = part['body']['data']
             decoded_data = base64.urlsafe_b64decode(data).decode('utf-8')
             if not body:
                 body = decoded_data

        # Identify Attachments (Metadata only)
        filename = part.get('filename')
        if filename and filename.lower().endswith('.pdf'):
            attachment_id = part['body'].get('attachmentId')
            inline_data = part['body'].get('data')

            attachments.append({
                "filename": filename,
                "attachmentId": attachment_id,
                "mimeType": part.get('mimeType'),
                "inlineData": inline_data # Might be None
            })

    # Clean the body
    newest_body = extract_latest_body(body)

    return newest_body, attachments, metadata

def fetch_attachment_blob(message_id: str, attachment: dict) -> Optional[bytes]:
    """
    Fetches the actual content of an attachment.
    """
    if attachment.get('inlineData'):
        return base64.urlsafe_b64decode(attachment['inlineData'])

    if attachment.get('attachmentId'):
        try:
            service = get_gmail_service()
            att = service.users().messages().attachments().get(
                userId='me', messageId=message_id, id=attachment['attachmentId']).execute()

            if 'data' in att:
                return base64.urlsafe_b64decode(att['data'])
        except Exception as e:
            logger.error(f"Failed to fetch attachment {attachment.get('filename')}: {e}")
            return None

    return None

def classify_email_status(body: str) -> EmailStatus:
    lower_body = body.lower()

    # Pre-alert keywords
    pre_alert_keywords = ["pre-alert", "pre alert", "pré-alerte", "prealert"]
    if any(x in lower_body for x in pre_alert_keywords):
        return EmailStatus.PRE_ALERT

    # Draft keywords
    draft_keywords = ["draft", "b/l draft", "bl draft", "b/l to confirm", "draft bl"]
    if any(x in lower_body for x in draft_keywords):
        return EmailStatus.DRAFT

    return EmailStatus.UNKNOWN
