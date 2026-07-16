from scripts.app import app
from database import db
import pytest

@pytest.fixture
def guest():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://:memory:'
    with app.test_client() as guest:
        with app.app_context():
            db.create_all()
            yield guest
            db.drop_all()

@pytest.fixture
def logged_in_user(guest):
    with guest.session_transaction() as session:
        session['email'] = 'unittest@example.com'
        session['password'] = 'test'
    return guest

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