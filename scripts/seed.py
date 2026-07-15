"""Populate the local SQLite database with demo users and message history.

Run from the project root:
    .venv/bin/python scripts/seed.py

The script is idempotent: it creates only missing demo users and messages.
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

from flask import Flask

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from database.db import db, init_db
from database.models import Message, User


DEMO_USERS = (
    {
        "email": "anna.demo@example.com",
        "name": "Anna",
        "surname": "Kowalska",
        "password": "DemoPassword123!",
    },
    {
        "email": "jan.demo@example.com",
        "name": "Jan",
        "surname": "Nowak",
        "password": "DemoPassword123!",
    },
)

DEMO_MESSAGES = (
    ("anna.demo@example.com", "Hi, are we still meeting at 5 PM today?", True),
    ("anna.demo@example.com", "Congratulations! Claim your prize now by clicking this link.", False),
    ("anna.demo@example.com", "Please send me the presentation when you have a moment.", True),
    ("anna.demo@example.com", "Your account will be closed today. Verify your password immediately.", False),
    ("anna.demo@example.com", "Thank you for your help with the project.", True),
    ("anna.demo@example.com", "You have been selected for a cash reward. Reply YES to claim it.", False),
    ("anna.demo@example.com", "I will call you after my appointment.", True),
    ("anna.demo@example.com", "URGENT: confirm your bank details at the attached website.", False),
    ("anna.demo@example.com", "The delivery should arrive tomorrow morning.", True),
    ("anna.demo@example.com", "Free gift card available now — enter your details to receive it.", False),
    ("anna.demo@example.com", "Could you pick up some bread on your way home?", True),
    ("anna.demo@example.com", "Final notice: pay the outstanding fee to avoid legal action.", False),
    ("jan.demo@example.com", "I have attached the notes from today's meeting.", True),
    ("jan.demo@example.com", "You won a new phone! Click here to arrange delivery.", False),
    ("jan.demo@example.com", "See you at the station at noon.", True),
)


def create_app():
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{PROJECT_ROOT / 'db.sqlite3'}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    init_db(app)
    return app


def seed():
    app = create_app()
    with app.app_context():
        users_created = 0
        messages_created = 0

        for user_data in DEMO_USERS:
            if User.query.get(user_data["email"]):
                continue
            user = User(
                email=user_data["email"],
                name=user_data["name"],
                surname=user_data["surname"],
            )
            user.set_password(user_data["password"])
            db.session.add(user)
            users_created += 1

        db.session.flush()
        start_date = datetime.now() - timedelta(days=len(DEMO_MESSAGES))
        for index, (email, value, is_ham) in enumerate(DEMO_MESSAGES):
            already_exists = Message.query.filter_by(email=email, value=value).first()
            if already_exists:
                continue
            db.session.add(Message(
                email=email,
                value=value,
                is_ham=is_ham,
                created_at=start_date + timedelta(days=index),
            ))
            messages_created += 1

        db.session.commit()
        print(f"Seed complete: {users_created} user(s), {messages_created} message(s) created.")
        print("Demo login: anna.demo@example.com / DemoPassword123!")
        print("Demo login: jan.demo@example.com / DemoPassword123!")


if __name__ == "__main__":
    seed()
