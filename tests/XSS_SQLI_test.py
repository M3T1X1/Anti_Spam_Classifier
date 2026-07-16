from unittest.mock import patch
from database.models import User, Message
from database import db
import pytest

SQLI_PAYLOADS = [
    "' OR '1'='1",
    "'; DROP TABLE users; --",
    "' OR 1=1 --",
    "admin'--",
    "' UNION SELECT * FROM users --",
]


@pytest.fixture
def existing_user(guest):
    with guest.application.app_context():
        user = User(email='victim@example.com', name='Vic', surname='Tim')
        user.set_password('correcthorse')
        db.session.add(user)
        db.session.commit()
    return guest




@pytest.mark.parametrize('payload', SQLI_PAYLOADS)
def test_login_email_sqli_does_not_bypass_auth(existing_user, payload):
    """A classic SQLi payload in the email field must not authenticate."""
    resp = existing_user.post('/login', data={
        'email': payload,
        'password': 'whatever'
    })
    assert resp.status_code == 302
    with existing_user.session_transaction() as sess:
        assert 'email' not in sess


@pytest.mark.parametrize('payload', SQLI_PAYLOADS)
def test_login_password_sqli_does_not_bypass_auth(existing_user, payload):
    """A classic SQLi payload in the password field must not authenticate."""
    resp = existing_user.post('/login', data={
        'email': 'victim@example.com',
        'password': payload
    })
    assert resp.status_code == 302
    with existing_user.session_transaction() as sess:
        assert 'email' not in sess


def test_register_sqli_payload_stored_as_literal_string(guest):
    """SQLi payload in registration fields should be stored verbatim as data,
    not interpreted as SQL, and the table should survive intact."""
    payload = "'; DROP TABLE users; --"
    resp = guest.post('/register', data={
        'email': 'sqli@example.com',
        'password': 'haslo123',
        'password_confirm': 'haslo123',
        'name': payload,
        'surname': 'Kowalski'
    })
    assert resp.status_code == 302

    with guest.application.app_context():
        user = User.query.filter_by(email='sqli@example.com').first()
        assert user is not None
        assert user.name == payload


@patch('scripts.app.get_classifier')
def test_dashboard_message_sqli_payload_stored_as_literal_string(mock_get_classifier, logged_in_user):
    """SQLi payload submitted as a message must be stored as plain text,
    and must not corrupt or drop the messages table."""
    mock_get_classifier.return_value = lambda text: [{'label': 'LABEL_0'}]
    payload = "'; DROP TABLE messages; --"

    resp = logged_in_user.post('/dashboard', data={'message': payload})
    assert resp.status_code == 200

    with logged_in_user.application.app_context():
        stored = Message.query.filter_by(value=payload).first()
        assert stored is not None
        assert Message.query.count() >= 1


XSS_PAYLOADS = [
    "<script>alert('xss')</script>",
    "<img src=x onerror=alert(1)>",
    "\"><script>alert(1)</script>",
    "<svg onload=alert(1)>",
]

@pytest.mark.parametrize('payload', XSS_PAYLOADS)
@patch('scripts.app.get_classifier')
def test_dashboard_message_xss_payload_is_escaped_in_response(mock_get_classifier, logged_in_user, payload):
    """A message containing an XSS payload must never be reflected
    as raw, executable HTML in the rendered dashboard."""
    mock_get_classifier.return_value = lambda text: [{'label': 'LABEL_0'}]

    resp = logged_in_user.post('/dashboard', data={'message': payload}, follow_redirects=True)
    body = resp.get_data(as_text=True)

    assert payload not in body
    if '<script>' in payload or '<img' in payload or '<svg' in payload:
        assert '<script>' not in body
        assert '<img src=x onerror=' not in body
        assert '<svg onload=' not in body


@pytest.mark.parametrize('payload', XSS_PAYLOADS)
def test_register_name_xss_payload_is_escaped_when_rendered(guest, payload):
    """If a stored name/surname is ever rendered back to the page
    (e.g. flash message, profile view), it must come out escaped."""
    resp = guest.post('/register', data={
        'email': 'xsstest@example.com',
        'password': 'haslo123',
        'password_confirm': 'haslo123',
        'name': payload,
        'surname': 'Kowalski'
    }, follow_redirects=True)

    body = resp.get_data(as_text=True)
    assert payload not in body


@patch('scripts.app.get_classifier')
def test_dashboard_message_xss_payload_stored_raw_but_rendered_safe(mock_get_classifier, logged_in_user):
    """DB should keep the original payload (that's fine and expected —
    escaping happens at render time, not at storage time)."""
    mock_get_classifier.return_value = lambda text: [{'label': 'LABEL_0'}]
    payload = "<script>alert('xss')</script>"

    logged_in_user.post('/dashboard', data={'message': payload})

    with logged_in_user.application.app_context():
        stored = Message.query.filter_by(value=payload).first()
        assert stored is not None
        assert stored.value == payload

    resp = logged_in_user.get('/dashboard')
    body = resp.get_data(as_text=True)
    assert '<script>alert' not in body