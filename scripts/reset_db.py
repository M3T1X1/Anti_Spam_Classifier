import sys
from pathlib import Path
from flask import Flask

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from database.db import db, init_db
from database.models import Message, User


def create_app():
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{PROJECT_ROOT / 'db.sqlite3'}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    init_db(app)
    return app


def reset_data():
    app = create_app()
    with app.app_context():
        try:
            num_messages = db.session.query(Message).delete()
            num_users = db.session.query(User).delete()

            db.session.commit()
            print(f"Database cleared: removed {num_messages} messages and {num_users} users.")
        except Exception as e:
            db.session.rollback()
            print(f"Error during data deletion: {e}")


if __name__ == "__main__":
    confirm = input("Are you sure you want to delete all data? (y/n): ")
    if confirm.lower() == 'y':
        reset_data()
    else:
        print("Operation cancelled.")