import os
import sys
import time
from pathlib import Path
from functools import wraps

base_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(base_dir))

from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
from sqlalchemy import func
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


@app.route("/favicon.png")
def favicon():
    """Serve the application favicon stored in the project root."""
    return send_from_directory(BASE_DIR, "favicon.png", mimetype="image/png")

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
    saved_message_id = None
    if request.method == "POST":
        user_input = request.form.get("message", "").strip()
        if user_input:
            try:
                predictions = get_classifier()(user_input)
                raw_label = predictions[0]['label']
                result = LABEL_MAP.get(raw_label, "unknown")

                # Only authenticated users have their analyses saved.
                if 'email' in session:
                    message = Message(
                        email=session['email'],
                        value=user_input,
                        is_ham=(result == 'ham'),
                    )
                    db.session.add(message)
                    db.session.commit()
                    saved_message_id = message.message_id
                else:
                    saved_message_id = None
            except Exception as err:
                db.session.rollback()
                print(f"Error message: {str(err)}")
                result = "Internal error"
                saved_message_id = None

    page = max(request.args.get('page', 1, type=int), 1)
    sort_by = request.args.get('sort', 'date_desc', type=str)
    filter_ham = request.args.get('filter', 'all', type=str)

    valid_sorts = {'date_desc', 'date_asc', 'type_asc', 'type_desc'}
    valid_filters = {'all', 'ham', 'not_ham'}
    if sort_by not in valid_sorts:
        sort_by = 'date_desc'
    if filter_ham not in valid_filters:
        filter_ham = 'all'

    # The table is shared: it shows all analyses saved by authenticated users.
    # Guest analyses are never added to this query because they are not persisted.
    query = Message.query

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
        saved_message_id=saved_message_id,
        user=session.get('name') if 'email' in session else None,
        is_guest='email' not in session
    )


@app.route("/message-feedback", methods=["POST"])
@login_required
def message_feedback():
    """Save the user's assessment of a classifier prediction."""
    message_id = request.form.get('message_id', type=int)
    feedback = request.form.get('feedback')

    if not message_id or feedback not in {'correct', 'incorrect'}:
        flash('Invalid prediction feedback.', 'danger')
        return redirect(url_for('dashboard'))

    message = Message.query.filter_by(
        message_id=message_id,
        email=session['email']
    ).first()
    if message is None:
        flash('This message cannot be rated.', 'danger')
        return redirect(url_for('dashboard'))

    message.is_correct = feedback == 'correct'
    db.session.commit()
    flash('Thank you for rating the prediction.', 'success')
    return redirect(url_for('dashboard'))


@app.route("/analytics", methods=["GET"])
@login_required
def analytics():
    """Show interactive classification statistics for the signed-in user."""
    scope = request.args.get('scope', 'all', type=str)
    if scope not in {'all', 'mine'}:
        scope = 'all'

    query = db.session.query(Message.is_ham, func.count(Message.message_id))
    if scope == 'mine':
        query = query.filter(Message.email == session['email'])

    classification_counts = dict(
        query
        .group_by(Message.is_ham)
        .all()
    )
    ham_count = classification_counts.get(True, 0)
    not_ham_count = classification_counts.get(False, 0)
    total_count = ham_count + not_ham_count

    feedback_query = db.session.query(Message.is_correct, func.count(Message.message_id))
    if scope == 'mine':
        feedback_query = feedback_query.filter(Message.email == session['email'])
    feedback_counts = dict(feedback_query.group_by(Message.is_correct).all())
    correct_count = feedback_counts.get(True, 0)
    incorrect_count = feedback_counts.get(False, 0)

    return render_template(
        "analytics.html",
        user=session.get('name'),
        scope=scope,
        ham_count=ham_count,
        not_ham_count=not_ham_count,
        total_count=total_count,
        correct_count=correct_count,
        incorrect_count=incorrect_count,
        unrated_count=total_count - correct_count - incorrect_count,
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


if __name__ == "__main__":
    app.run(debug=True)
