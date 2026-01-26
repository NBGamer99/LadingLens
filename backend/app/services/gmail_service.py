import os.path
import base64
from typing import List, Tuple, Optional
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import logging

from app.config import settings
from app.models.schemas import EmailStatus

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

logger = logging.getLogger(__name__)


import re

def get_gmail_service():
    creds = None
    if os.path.exists(settings.GMAIL_TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(settings.GMAIL_TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(settings.GMAIL_CREDENTIALS_FILE):
                raise FileNotFoundError(f"Credentials file {settings.GMAIL_CREDENTIALS_FILE} not found. Please add it to the backend directory.")

            flow = InstalledAppFlow.from_client_secrets_file(
                settings.GMAIL_CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(settings.GMAIL_TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())

    return build('gmail', 'v1', credentials=creds)

def fetch_recent_emails(limit: int = 10) -> List[dict]:
    service = get_gmail_service()
    results = service.users().messages().list(userId='me', maxResults=limit).execute()
    messages = results.get('messages', [])

    email_data = []
    for msg in messages:
        # We only need 'full' format to get the body structure,
        # but we don't strictly need to download massive attachments yet if we look at structure.
        # However, for simplicity, 'full' is fine as long as we don't eagerly download attachment data blobb.
        # The 'get' method with format='full' does return attachment metadata but not the data itself usually unless requested?
        # Actually standard Gmail API 'full' returns payload but attachment data is a separate ID reference usually,
        # unless it's small.
        full_msg = service.users().messages().get(userId='me', id=msg['id']).execute()
        email_data.append(full_msg)

    return email_data

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

    # We split by these patterns and take the first part.

    # Regex for "On <date> <person> wrote:"
    # This handles various date formats and variations
    on_wrote_pattern = r'On\s+.*wrote:[\s\S]*'

    # Regex for original message block
    original_msg_pattern = r'-+\s*Original Message\s*-+[\s\S]*'

    # Regex for From: header block usually found in forwards/replies
    # Captures "From: ... \n Date: ..." or "From: ... \n Sent: ..."
    # allowing for indentation
    from_header_pattern = r'\n\s*From:.*[\r\n]+\s*(?:Sent|Date):.*[\s\S]*'

    # Regex for "Sent from my" signature
    sent_from_pattern = r'\n\s*Sent from my.*'

    cleaned = body

    # specific explicit splitters first (simple strings)
    simple_splitters = ["-----Original Message-----", "----- Original Message -----"]
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
        "source_received_at": message.get('internalDate') # Timestamp ms
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
            # Sometimes data is inline if small
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
