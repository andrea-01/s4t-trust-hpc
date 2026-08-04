import os
import httpx
import pytest

MAILPIT_API = os.getenv("MAILPIT_API_URL", "http://localhost:8025/api/v1/messages")

@pytest.mark.integration
def test_mailpit_receives_email():
    """
    Integration test. It requires mailpit to be running and a notification to be sent.
    We just check that mailpit's API is accessible and returns a valid response.
    Ideally, we'd trigger an on-chain event and wait for the email here,
    but verifying Mailpit's state is a good start.
    """
    try:
        response = httpx.get(MAILPIT_API)
        assert response.status_code == 200
        data = response.json()
        assert "messages" in data
        assert isinstance(data["messages"], list)
    except httpx.RequestError as e:
        pytest.fail(f"Could not connect to Mailpit at {MAILPIT_API}. Is it running? Error: {e}")
