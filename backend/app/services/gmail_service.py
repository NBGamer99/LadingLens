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
        full_msg = service.users().messages().get(userId='me', id=msg['id']).execute()
        email_data.append(full_msg)

    return email_data

def get_header(headers: List[dict], name: str) -> str:
    for h in headers:
        if h['name'].lower() == name.lower():
            return h['value']
    return ""

def parse_email_message(message: dict) -> Tuple[str, List[dict], dict]:
    """
    Returns: (newest_body, attachments, metadata)
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
             # quick fix: only grab the first text part.
             # TODO: usually the first one is the actual body, subsequent ones might be html/signatures.
             if not body:
                 body = decoded_data

        # Extract Attachments
        filename = part.get('filename')
        if filename and filename.lower().endswith('.pdf'):
            if 'data' in part['body']:
                file_data = part['body']['data']
            elif 'attachmentId' in part['body']:
                 service = get_gmail_service()
                 att = service.users().messages().attachments().get(
                    userId='me', messageId=message['id'], id=part['body']['attachmentId']).execute()
                 file_data = att['data']
            else:
                file_data = None

            if file_data:
                attachments.append({
                    "filename": filename,
                    "data": base64.urlsafe_b64decode(file_data)
                })

    return body, attachments, metadata

def classify_email_status(body: str) -> EmailStatus:
    # trying to grab just the latest message.
    # TODO: improve this, maybe use a library like email-reply-parser?
    # Ideally we should strip quoted text first.

    lower_body = body.lower()

    # Simple splitting for newest body
    separators = ["-----original message-----", "from:", "on ... wrote:", "sent from my"]
    for sep in separators:
        if sep in lower_body:
            lower_body = lower_body.split(sep)[0]

    if any(x in lower_body for x in ["pre-alert", "pre alert", "pré-alerte", "prealert"]):
        return EmailStatus.PRE_ALERT

    if any(x in lower_body for x in ["draft", "b/l draft", "bl draft", "b/l to confirm"]):
        return EmailStatus.DRAFT

    return EmailStatus.UNKNOWN
