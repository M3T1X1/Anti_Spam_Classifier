from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, text

db = SQLAlchemy()


def init_db(app):
    """Initialize the database with the Flask app"""
    db.init_app(app)
    with app.app_context():
        db.create_all()
        _migrate_messages_table()
        print("Database tables created successfully!")


def _migrate_messages_table():
    """Add columns introduced after the initial SQLite schema was created."""
    message_columns = {
        column["name"] for column in inspect(db.engine).get_columns("messages")
    }
    if "is_correct" not in message_columns:
        db.session.execute(text("ALTER TABLE messages ADD COLUMN is_correct BOOLEAN"))
        db.session.commit()
