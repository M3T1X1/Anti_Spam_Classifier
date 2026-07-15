import os
import sys
import time
from pathlib import Path
from functools import wraps

# Add parent directory to path so we can import database module
sys.path.insert(0, str(Path(__file__).parent.parent))

from flask import Flask, render_template, request, redirect, url_for, session, flash
from transformers import pipeline
from database.models import User, Message, Plot
from database.db import db, init_db


os.environ["HF_HUB_OFFLINE"] = "1"

CURRENT_FILE = Path(__file__).resolve()
BASE_DIR = CURRENT_FILE.parent.parent
MODEL_DIR = str(BASE_DIR / 'distilbert_spam_model' )
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'db.sqlite3')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'your-secret-key-change-this'
init_db(app)


classifier = None

def get_classifier():
    global classifier
    if classifier is None:
        print(f"Local model loading from: {MODEL_DIR}...")

        start_time = time.time()
        try:
            classifier = pipeline(
                "text-classification",
                model=MODEL_DIR,
                tokenizer=MODEL_DIR,
                device=-1,
                local_files_only=True
            )

            elapsed_time = time.time() - start_time
            print(f"Model loaded in: {elapsed_time:.4f} seconds.")

        except Exception as e:
            elapsed_time = time.time() - start_time
            print(f"\nModel failed after {elapsed_time:.4f} seconds.")
            print(f"Error message: {str(e)}\n")
            raise e

    return classifier


def login_required(f):
    """Decorator to require login for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'email' not in session:
            flash('Please log in to access this page', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


LABEL_MAP = {
    'LABEL_0': 'ham', 'LABEL_1': 'spam', 'LABEL_2': 'smishing',
    'ham': 'ham', 'spam': 'spam', 'smishing': 'smishing'
}

@app.route("/register", methods=["GET", "POST"])
def register():
    """User registration"""
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        password_confirm = request.form.get("password_confirm")
        name = request.form.get("name")
        surname = request.form.get("surname")

        if not all([email, password, password_confirm, name, surname]):
            flash('All fields are required', 'danger')
            return redirect(url_for('register'))

        if password != password_confirm:
            flash('Passwords do not match', 'danger')
            return redirect(url_for('register'))

        if len(password) < 6:
            flash('Password must be at least 6 characters long', 'danger')
            return redirect(url_for('register'))

        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'danger')
            return redirect(url_for('register'))

        user = User(email=email, name=name, surname=surname)
        user.set_password(password)

        try:
            db.session.add(user)
            db.session.commit()
            flash('Registration successful! You can now log in.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash(f'Registration error: {str(e)}', 'danger')
            return redirect(url_for('register'))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """User login"""
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        if not email or not password:
            flash('Email and password are required', 'danger')
            return redirect(url_for('login'))

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            session['email'] = email
            session['name'] = user.name
            session['surname'] = user.surname
            flash(f'Logged in as {user.name} {user.surname}!', 'success')
            return redirect(url_for('index'))

        flash('Invalid email or password', 'danger')
        return redirect(url_for('login'))

    return render_template("login.html")


@app.route("/logout")
def logout():
    """User logout"""
    session.clear()
    flash('Logged out successfully', 'info')
    return redirect(url_for('login'))


@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    """Main classifier page"""
    result = None
    if request.method == "POST":
        user_input = request.form.get("message")
        if user_input and user_input.strip():
            try:
                clf = get_classifier()
                predictions = clf(user_input.strip())

                print("User message: ", user_input)
                print(f"[DEBUG RAW PREDICTION] {predictions}")
                raw_label = predictions[0]['label']
                result = LABEL_MAP.get(raw_label, "unknown")
                print(f"[DEBUG MAPPED RESULT] {result}")

                message = Message(
                    email=session['email'],
                    value=user_input.strip(),
                    is_ham=(result == 'ham')
                )
                db.session.add(message)
                db.session.commit()

            except Exception as err:
                print(f"Error message: {str(err)}")
                result = f"Internal error"

    return render_template("index.html", result=result, user=session.get('name'))


if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)