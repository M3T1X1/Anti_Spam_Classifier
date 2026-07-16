def test_home_should_200(guest):
    resp = guest.get('/', follow_redirects=True)
    assert resp.status_code == 200

def test_dashboard_should_200(guest):
    assert guest.get('/dashboard').status_code == 200

def test_login_should_200(guest):
    assert guest.get('/login').status_code == 200

def test_register_should_200(guest):
    assert guest.get('/register').status_code == 200

def test_logout_should_302(guest):
    assert guest.get('/logout').status_code == 302

def test_analytics_should_302(guest):
    assert guest.get('/analytics').status_code == 302

def test_register_success_should_302(guest):
    resp = guest.post('/register', data={
        'email': 'nowy@example.com',
        'password': 'haslo123',
        'name': 'Jan',
        'surname': 'Kowalski'
    })
    assert resp.status_code == 302

def test_register_password_mismatch_should_302(guest):
    resp = guest.post('/register', data={
        'email': 'a@example.com',
        'password': 'haslo123',
        'name': 'Jan',
        'surname': 'Kowalski'
    })
    assert resp.status_code == 302

def test_login_wrong_password_should_302_and_no_session(guest):
    resp = guest.post('/login', data={'email': 'x@example.com', 'password': 'zle'})
    assert resp.status_code == 302
    with guest.session_transaction() as sess:
        assert 'email' not in sess

def test_logout_clears_session(logged_in_user):
    resp = logged_in_user.get('/logout')
    assert resp.status_code == 302
    with logged_in_user.session_transaction() as sess:
        assert 'email' not in sess