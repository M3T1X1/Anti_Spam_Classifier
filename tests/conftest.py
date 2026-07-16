from scripts.app import app
from database import db
import pytest

@pytest.fixture
def guest():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
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