def test_message_feedback_requires_login(guest):
    resp = guest.post('/message-feedback', data={'message_id': 1, 'feedback': 'correct'})
    assert resp.status_code == 302