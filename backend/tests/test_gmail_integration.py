import pytest
from app.services.gmail_service import fetch_recent_emails

def test_fetch_recent_emails_integration():
    """
    Integration test for Gmail Service.
    Verifies that we can authenticate and retrieve emails using the stored credentials.
    """
    print("\nStarting Gmail Integration Test...")

    # Attempt to fetch emails
    try:
        emails = fetch_recent_emails(limit=5)
    except Exception as e:
        pytest.fail(f"Failed to fetch emails: {e}")

    # Assertions
    assert isinstance(emails, list), "Result should be a list"
    # We might not have 5 emails, but the call should succeed.
    # If the user has an empty inbox, this length check might fail if strict.
    # But usually checks for non-None is good enough for basic connectivity.

    print(f"Successfully retrieved {len(emails)} emails.")

    for email in emails:
        headers = email.get('payload', {}).get('headers', [])
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
        print(f"- Found Email Subject: {subject}")

    # If we reached here without exception, basic auth works.
