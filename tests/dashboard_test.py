from unittest.mock import patch


def test_home_should_200(guest):
    resp = guest.get('/', follow_redirects=True)
    assert resp.status_code == 200


def test_dashboard_should_200(guest):
    assert guest.get('/dashboard').status_code == 200


@patch('scripts.app.get_classifier')
def test_dashboard_post_ham_saves_message(mock_get_classifier, logged_in_user):
    mock_get_classifier.return_value = lambda text: [{'label': 'LABEL_0'}]
    resp = logged_in_user.post('/dashboard', data={'message': 'Hello there'})
    assert resp.status_code == 200


@patch('scripts.app.get_classifier')
def test_dashboard_post_guest_does_not_save(mock_get_classifier, guest):
    mock_get_classifier.return_value = lambda text: [{'label': 'LABEL_1'}]
    resp = guest.post('/dashboard', data={'message': 'Free money now'})
    assert resp.status_code == 200


def test_analyze_redirects_to_dashboard(logged_in_user):
    resp = logged_in_user.get('/analyze')
    assert resp.status_code == 302


def test_guest_redirects_to_dashboard(guest):
    resp = guest.get('/guest')
    assert resp.status_code == 302