import os
import sys
import time
from pathlib import Path
from functools import wraps

# Add parent directory to path BEFORE imports
base_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(base_dir))

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

LABEL_MAP = {
    'LABEL_0': 'ham', 'LABEL_1': 'spam', 'LABEL_2': 'smishing',
    'ham': 'ham', 'spam': 'spam', 'smishing': 'smishing'
}


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
            return redirect(url_for('dashboard'))

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
def index_redirect():
    """Redirect to dashboard or handle a legacy analyser form submission."""
    if 'email' in session:
        if request.method == "POST":
            return dashboard()
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    """Analyse a message and display the signed-in user's saved history."""
    result = None
    if request.method == "POST":
        user_input = request.form.get("message", "").strip()
        if user_input:
            try:
                predictions = get_classifier()(user_input)
                raw_label = predictions[0]['label']
                result = LABEL_MAP.get(raw_label, "unknown")

                # Only authenticated users have their analyses saved.
                if 'email' in session:
                    db.session.add(Message(
                        email=session['email'],
                        value=user_input,
                        is_ham=(result == 'ham')
                    ))
                    db.session.commit()
            except Exception as err:
                db.session.rollback()
                print(f"Error message: {str(err)}")
                result = "Internal error"

    page = max(request.args.get('page', 1, type=int), 1)
    sort_by = request.args.get('sort', 'date_desc', type=str)
    filter_ham = request.args.get('filter', 'all', type=str)

    valid_sorts = {'date_desc', 'date_asc', 'type_asc', 'type_desc'}
    valid_filters = {'all', 'ham', 'not_ham'}
    if sort_by not in valid_sorts:
        sort_by = 'date_desc'
    if filter_ham not in valid_filters:
        filter_ham = 'all'

    # Only messages belonging to the currently logged-in user are visible.
    # Guests can open this page but have no persisted history.
    if 'email' in session:
        query = Message.query.filter_by(email=session['email'])
    else:
        query = Message.query.filter_by(email='')

    # Apply filter
    if filter_ham == 'ham':
        query = query.filter_by(is_ham=True)
    elif filter_ham == 'not_ham':
        query = query.filter_by(is_ham=False)

    # Apply sorting
    if sort_by == 'date_asc':
        query = query.order_by(Message.created_at.asc())
    elif sort_by == 'type_asc':
        query = query.order_by(Message.is_ham.asc(), Message.created_at.desc())
    elif sort_by == 'type_desc':
        query = query.order_by(Message.is_ham.desc(), Message.created_at.desc())
    else:
        query = query.order_by(Message.created_at.desc())

    # Paginate
    paginated = query.paginate(page=page, per_page=10, error_out=False)
    messages = paginated.items
    total_pages = paginated.pages

    return render_template(
        "dashboard.html",
        messages=messages,
        page=page,
        total_pages=total_pages,
        sort_by=sort_by,
        filter_ham=filter_ham,
        result=result,
        user=session.get('name') if 'email' in session else None,
        is_guest='email' not in session
    )


@app.route("/analyze", methods=["GET", "POST"])
@login_required
def try_classifier():
    """Backward-compatible route for the former standalone analyser."""
    return redirect(url_for('dashboard'))


@app.route("/guest", methods=["GET", "POST"])
def guest():
    """Guest mode uses the dashboard without persisting analyses."""
    return redirect(url_for('dashboard'))


if __name__ == "__main__":testowy123@wp.pl
    app.run(debug=True, use_reloader=False)
