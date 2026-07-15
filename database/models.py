from .db import db
from werkzeug.security import generate_password_hash, check_password_hash

class User(db.Model):
    __tablename__ = 'users'
    email = db.Column(db.String, primary_key=True)
    password = db.Column(db.String, nullable=False)
    name = db.Column(db.String, nullable=False)
    surname = db.Column(db.String, nullable=False)
    role = db.Column(db.String, default='user')
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    modified_at = db.Column(db.DateTime, onupdate=db.func.now())

    def set_password(self, password):
        """Hash and set password"""
        self.password = generate_password_hash(password)

    def check_password(self, password):
        """Verify password hash"""
        return check_password_hash(self.password, password)

    def __repr__(self):
        return f'<User {self.email}>'

class Message(db.Model):
    __tablename__ = 'messages'
    message_id = db.Column(db.Integer, primary_key=True)
    value = db.Column(db.String(10000))
    is_ham = db.Column(db.Boolean)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

class Plot(db.Model):
    __tablename__ = 'plots'
    plot_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    path = db.Column(db.String)
    plot_name = db.Column(db.String)