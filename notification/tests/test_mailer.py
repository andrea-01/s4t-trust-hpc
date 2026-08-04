from unittest.mock import patch, MagicMock
from notification.app.mailer import send_onboarding_email

@patch('smtplib.SMTP')
def test_send_onboarding_email(mock_smtp):
    mock_server = MagicMock()
    mock_smtp.return_value.__enter__.return_value = mock_server
    
    send_onboarding_email("test@example.com", "dev-123", 42, "0xabc")
    
    mock_server.send_message.assert_called_once()
    
    sent_msg = mock_server.send_message.call_args[0][0]
    assert sent_msg['To'] == "test@example.com"
    assert "dev-123" in sent_msg.get_content()
    assert "42" in sent_msg.get_content()
    assert "0xabc" in sent_msg.get_content()
