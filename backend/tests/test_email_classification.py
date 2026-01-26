
import pytest
from app.services.gmail_service import classify_email_status, extract_latest_body
from app.models.schemas import EmailStatus

def test_extract_latest_body_simple():
    body = "This is the latest message."
    assert extract_latest_body(body) == "This is the latest message."

def test_extract_latest_body_with_original_message():
    body = """Here is the draft.

    -----Original Message-----
    From: Some Guy
    Sent: Yesterday

    Old stuff."""

    clean = extract_latest_body(body)
    assert "Here is the draft" in clean
    assert "Old stuff" not in clean

def test_extract_latest_body_with_on_wrote():
    body = """Please review this pre-alert.

    On Mon, Jan 1, 2024 at 10:00 AM Some Guy wrote:
    > Quoted text
    """
    clean = extract_latest_body(body)
    assert "Please review this pre-alert" in clean
    assert "Quoted text" not in clean

def test_extract_latest_body_with_from_header():
    body = """Attached is the doc.

    From: Sender Name <sender@example.com>
    Date: Today
    """
    clean = extract_latest_body(body)
    assert "Attached is the doc" in clean
    assert "Date: Today" not in clean

def test_classify_pre_alert():
    bodies = [
        "This is a pre-alert for shipment X.",
        "Please see attached PRE ALERT",
        "Voici la pré-alerte",
        "Sending prealert now."
    ]
    for b in bodies:
        assert classify_email_status(b) == EmailStatus.PRE_ALERT

def test_classify_draft():
    bodies = [
        "Here is the draft bl for review.",
        "Please confirm this b/l draft.",
        "Attached is the DRAFT bill.",
        "B/L to confirm attached."
    ]
    for b in bodies:
        assert classify_email_status(b) == EmailStatus.DRAFT

def test_classify_unknown():
    bodies = [
        "Just say hi.",
        "Here is the invoice.",
        "Please reply."
    ]
    for b in bodies:
        assert classify_email_status(b) == EmailStatus.UNKNOWN
