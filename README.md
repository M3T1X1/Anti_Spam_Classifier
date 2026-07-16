# Anti_Spam_Classifier — Project Documentation

**Repository:** [github.com/M3T1X1/Anti_Spam_Classifier](https://github.com/M3T1X1/Anti_Spam_Classifier)
**Author:** M3T1X1 (Kacper Dusza)
**License:** MIT (© 2026 Kacper Dusza)
**Description:** A machine learning system that classifies text messages into three categories — **ham** (legitimate), **spam**, and **smishing** (SMS phishing) — served through a Flask web application with user accounts, message history, and analytics.

---

## 1. Overview

The project combines three layers:

1. **ML pipeline** — a fine-tuned **DistilBERT** transformer model trained to classify messages as `ham`, `spam`, or `smishing`.
2. **Data pipeline** — a sentence-level augmentation script that expands the labeled dataset before training.
3. **Web application** — a Flask app with authentication, a message analyzer, a saved-history dashboard, and an analytics page with interactive charts.

The application is designed to run fully offline/locally: the trained model is loaded from disk (`HF_HUB_OFFLINE=1`), and data is stored in a local SQLite database.

## 2. Repository Structure

| Path | Description |
|---|---|
| `run.py` | Main entry point: runs the test suite, initializes the DB, seeds demo data, starts the Flask dev server |
| `requirements.txt` | Python dependencies (123 packages) |
| `dataset.csv` | Original labeled dataset (`TEXT`, `LABEL`) |
| `dataset_augmented.csv` | Augmented dataset produced by `data_augmentation.py` |
| `ERD.png` | Entity-Relationship Diagram of the database schema |
| `favicon.png` | Application favicon, served at `/favicon.png` |
| `LICENSE` | MIT License |
| `.gitignore` | Git ignore rules |
| `scripts/app.py` | Flask application: routes, authentication, classification logic |
| `scripts/data_augmentation.py` | Sentence-splitting data augmentation script |
| `scripts/pipline_setup.py` | DistilBERT fine-tuning / training pipeline |
| `scripts/reset_db.py` | CLI utility to wipe all users and messages from the database |
| `scripts/seed.py` | Idempotent script that populates the DB with demo users/messages |
| `database/db.py` | SQLAlchemy `db` instance and `init_db(app)` initializer *(not directly retrieved, inferred from imports)* |
| `database/models.py` | SQLAlchemy models: `User`, `Message`, `Plot` *(not directly retrieved, inferred from usage)* |
| `scripts/templates/*.html` | Jinja2 templates: `login.html`, `register.html`, `dashboard.html`, `analytics.html` |
| `scripts/static/style.css` | Application stylesheet (dark theme) |
| `tests/conftest.py` | Pytest fixtures (`guest`, `logged_in_user`) — in-memory SQLite test DB |
| `tests/auth_test.py` | Authentication and routing tests |
| `tests/dashboard_test.py` | Message analysis / dashboard behavior tests |
| `tests/analytical_test.py` | Access-control tests for the `/analytics` route |
| `tests/feedback_test.py` | Access-control test for the `/message-feedback` route |
| `tests/test_static.py` | Static asset serving test (`/favicon.png`) |
| `tests/XSS_SQLI_test.py` | Security tests: SQL injection and XSS resistance |

### Language breakdown (per GitHub)
- Python — 52.3%
- HTML — 31.3%
- CSS — 16.4%

## 3. Tech Stack

**Backend / Web**
- Flask 3.1.3, Flask-SQLAlchemy (via `database.db`), Jinja2, Werkzeug

**Machine Learning / NLP**
- PyTorch, Hugging Face `transformers` (DistilBERT), `datasets`, `tokenizers`, `accelerate`
- scikit-learn (train/test split, metrics), NLTK (sentence tokenization)

**Data & Visualization**
- pandas, NumPy
- Chart.js (client-side charts), jsPDF (client-side PDF export)
- matplotlib / seaborn (used during offline training for the confusion matrix)

**Testing**
- pytest, with an in-memory SQLite database per test and `unittest.mock.patch` for mocking the classifier

**Notable extra dependencies present in `requirements.txt`** (not directly exercised by the code reviewed): `evidently` (ML monitoring/drift detection), `streamlit`, `Faker`, `dynaconf`, `litestar`/`uvicorn` — these suggest exploratory or planned tooling beyond the current Flask app.

## 4. Machine Learning Pipeline

### 4.1 Dataset

`dataset.csv` / `dataset_augmented.csv` use a simple two-column schema:

```csv
TEXT,LABEL
"Dont forget you can place as many FREE Requests with 1stchoice.co.uk as you wish.",spam
"you exist present with a £2000 bonus prize, call 09066364529",smishing
"Sorry * was at the grocers.",ham
```

Three classes are used: **`ham`**, **`spam`**, **`smishing`**.

The augmented dataset (`dataset_augmented.csv`) contains **16,371 rows** with the following class distribution:

| Label | Count |
|---|---|
| ham | 6,731 |
| smishing | 5,515 |
| spam | 4,125 |

> Note the text shows signs of prior automated paraphrasing/normalization (e.g. "you exist present with" instead of "you have been presented with"), consistent with augmentation via back-translation or a synonym-substitution technique in addition to the sentence-splitting method described below.

### 4.2 Data Augmentation (`scripts/data_augmentation.py`)

This script expands the dataset **by splitting multi-sentence messages into their constituent sentences**, each inheriting the original label:

- Reads `dataset.csv` via pandas.
- For every row, keeps the original full text, and additionally splits it into sentences using NLTK's `sent_tokenize` (`punkt`/`punkt_tab` models, downloaded on demand).
- Each resulting sentence is kept as a new training example only if it has **at least 3 words** (`min_words=3`).
- Duplicate texts are dropped (`drop_duplicates`), and the final dataset is shuffled (`random_state=42`).
- Output is written to `dataset_augmented.csv`.

This is a lightweight, deterministic augmentation strategy that increases dataset size and helps the model generalize to shorter, sentence-level inputs (useful since real SMS/messages are often short).

### 4.3 Model Training (`scripts/pipline_setup.py`)

Trains a **DistilBERT** sequence classifier (`distilbert-base-uncased`) for 3-class classification:

1. Loads `dataset_augmented.csv`, maps labels to integers: `{'ham': 0, 'spam': 1, 'smishing': 2}`.
2. Splits into train/test (90/10) with **stratified sampling** on the label.
3. Converts to Hugging Face `Dataset` objects and tokenizes with `DistilBertTokenizerFast` (max length 128, padding to max length).
4. Loads `DistilBertForSequenceClassification` with `num_labels=3` and explicit `id2label`/`label2id` mappings.
5. Trains using Hugging Face `Trainer` with:
   - 3 epochs, batch size 64 (train & eval), `fp16=True` (mixed precision)
   - Learning rate `3e-5`, weight decay `0.1`, warmup ratio `0.1`
   - Evaluation and checkpointing every epoch, best model loaded at the end (by lowest `eval_loss`)
6. After training, computes test accuracy and a full `classification_report` (precision/recall/F1 per class).
7. Saves the fine-tuned model and tokenizer to `../distilbert_spam_model/` — **this is the exact directory the Flask app (`scripts/app.py`) loads at runtime** (`MODEL_DIR = BASE_DIR / 'distilbert_spam_model'`).
8. Plots a confusion matrix with seaborn/matplotlib for visual inspection.

> The training script uses relative paths (`../dataset_augmented.csv`, `../distilbert_spam_model`), so it is meant to be run **from inside the `scripts/` directory**.

## 5. Web Application (`scripts/app.py`)

A single-file Flask application (~325 lines) providing authentication, message classification, history browsing, and analytics.

### 5.1 Configuration
- SQLite database at `<project_root>/db.sqlite3` (`SQLALCHEMY_DATABASE_URI`).
- `app.secret_key` is hardcoded as `'your-secret-key-change-this'` — **must be replaced with a secure random value before any real deployment.**
- `HF_HUB_OFFLINE=1` forces Hugging Face libraries to avoid network calls, and the classifier pipeline is loaded with `local_files_only=True`, ensuring the app never tries to download the model at runtime.

### 5.2 Classifier loading (lazy singleton)
`get_classifier()` lazily loads a Hugging Face `text-classification` pipeline from the local `distilbert_spam_model` directory the first time it's needed, caching it in a module-level `classifier` variable (loaded on CPU, `device=-1`). Predicted labels (`LABEL_0`, `LABEL_1`, `LABEL_2`) are mapped to human-readable names via `LABEL_MAP`:

```python
LABEL_MAP = {
    'LABEL_0': 'ham', 'LABEL_1': 'spam', 'LABEL_2': 'smishing',
    'ham': 'ham', 'spam': 'spam', 'smishing': 'smishing'
}
```

### 5.3 Routes

| Route | Methods | Auth required | Purpose |
|---|---|---|---|
| `/favicon.png` | GET | No | Serves the favicon from the project root |
| `/register` | GET, POST | No | User sign-up with validation (all fields required, password confirmation, min. 6-character password, duplicate-email check); passwords are hashed via `User.set_password()` |
| `/login` | GET, POST | No | Authenticates via `User.check_password()`; stores `email`, `name`, `surname` in the session |
| `/logout` | GET | No | Clears the session |
| `/` | GET, POST | No | Redirects logged-in users to `/dashboard` (or proxies a POST there); redirects guests to `/login` |
| `/dashboard` | GET, POST | No (dual mode) | Core feature: submits a message to the classifier, shows the result, and lists paginated message history with sorting/filtering. Only **authenticated** users' analyses are persisted to the DB; guests get a live prediction without storage |
| `/message-feedback` | POST | Yes | Lets a user mark a previous prediction as `correct`/`incorrect`, restricted to messages they own |
| `/analytics` | GET | Yes | Shows aggregate classification counts (ham vs. not-ham) and feedback accuracy counts, either scoped to `all` messages or `mine` |
| `/analyze` | GET, POST | Yes | Legacy route, redirects to `/dashboard` |
| `/guest` | GET, POST | No | Legacy route, redirects to `/dashboard` |

### 5.4 Dashboard behavior in detail

- On POST, the submitted message is classified; if the user is logged in, a `Message` row is created (`email`, `value`, `is_ham`) and its ID is returned to the template so a feedback widget (👍/👎) can be shown immediately.
- The message table supports:
  - **Filtering**: `all`, `ham`, `not_ham`
  - **Sorting**: `date_desc` (default), `date_asc`, `type_asc`, `type_desc`
  - **Pagination**: 10 messages per page via SQLAlchemy's `paginate()`
- Note: the history table displays **all users' saved messages**, not just the current user's — it is a shared analysis log rather than a private history.

### 5.5 Analytics behavior in detail

- Counts messages grouped by `is_ham` (ham vs. not-ham) and by `is_correct` (correct / incorrect / not yet rated), either across all messages or filtered to the current user's own (`scope=mine`).
- The `analytics.html` template renders two Chart.js bar charts (classification breakdown, feedback accuracy) with client-side **JPG and PDF export** (via `jsPDF`).

## 6. Database Schema (inferred from usage)

The exact contents of `database/models.py` and `database/db.py` could not be retrieved directly, but the schema can be reconstructed with confidence from how the models are used across `app.py`, `seed.py`, `reset_db.py`, and the test suite:

### `User`
| Field | Notes |
|---|---|
| `email` | Primary key (`User.query.get(email)` is used as a PK lookup) |
| `name` | First name |
| `surname` | Last name |
| *(hashed password)* | Not a plain column access; set via `set_password()`, verified via `check_password()` — almost certainly a hashed field using Werkzeug's password hashing utilities |

### `Message`
| Field | Notes |
|---|---|
| `message_id` | Primary key (auto-increment, referenced as `message.message_id`) |
| `email` | Foreign key to `User.email` — owner of the analysis |
| `value` | The analyzed message text |
| `is_ham` | Boolean — `True` if classified/labeled as ham, `False` otherwise (spam or smishing) |
| `is_correct` | Nullable boolean — user feedback on the prediction (`True`=correct, `False`=incorrect, `None`=not yet rated) |
| `created_at` | Timestamp, used for sorting and display |

### `Plot`
Imported in `app.py` (`from database.models import User, Message, Plot`) but **not referenced anywhere in the routes shown** — likely a reserved/in-progress model, possibly intended for persisting analytics chart snapshots or export history.

> See `ERD.png` in the repository root for the authoritative, diagrammed schema.

## 7. Operational Scripts

### `scripts/seed.py`
Idempotent demo-data seeder, run standalone (`python scripts/seed.py`) or automatically by `run.py`:
- Creates two demo users if they don't already exist:
  - `anna.demo@example.com` / `DemoPassword123!`
  - `jan.demo@example.com` / `DemoPassword123!`
- Inserts 15 realistic demo messages (mix of ham/spam-style text) with staggered `created_at` timestamps and a mix of feedback states (correct/incorrect), skipping any message that already exists for that user.

### `scripts/reset_db.py`
A destructive CLI utility that deletes **all** `Message` and `User` rows after an interactive `y/n` confirmation prompt. Intended for local development resets, not for production use (no safeguards beyond the console prompt).

## 8. Test Suite

Tests run via `pytest tests/ -v`, and are triggered automatically every time `run.py` starts (the app refuses to launch if any test fails — see Section 9).

### `conftest.py` — shared fixtures
- `guest`: a Flask test client with `TESTING=True` and an **in-memory SQLite** database (`sqlite:///:memory:`), created fresh (`db.create_all()`) and torn down (`db.drop_all()`) per test.
- `logged_in_user`: builds on `guest`, injecting `email`/`password` directly into the test session to simulate an authenticated user without going through `/login`.

### `auth_test.py`
Covers basic route availability and status codes for guests (`/`, `/dashboard`, `/login`, `/register` → 200; `/logout`, `/analytics` → 302), plus registration/login edge cases: successful registration, password-mismatch handling, wrong-password login (and confirms no session is created), and session clearing on logout.

### `dashboard_test.py`
Verifies the dashboard is reachable, that posting a message with a **mocked classifier** (`@patch('scripts.app.get_classifier')`) works for both a logged-in user (message gets saved) and a guest (message is classified but not saved), and that the legacy `/analyze` and `/guest` routes redirect to `/dashboard`.

### `analytical_test.py`
Confirms `/analytics` requires authentication (302 for guests, 200 for logged-in users).

### `feedback_test.py`
Confirms `/message-feedback` requires authentication (302 for guests).

### `test_static.py`
Confirms `/favicon.png` is served successfully (200).

### `XSS_SQLI_test.py` — security regression tests
A notably thorough security-focused suite:
- **SQL injection**: parametrized tests with classic payloads (`' OR '1'='1`, `'; DROP TABLE users; --`, `admin'--`, UNION-based payloads, etc.) submitted via the login form's email and password fields, asserting authentication is never bypassed and no session is created.
- Confirms SQLi-like payloads submitted through registration (`name` field) or the dashboard (`message` field) are stored **verbatim as literal strings** rather than being interpreted as SQL — and that the corresponding tables survive intact (protection provided naturally by SQLAlchemy's parameterized queries).
- **XSS**: parametrized tests with common payloads (`<script>alert('xss')</script>`, `<img src=x onerror=alert(1)>`, `<svg onload=alert(1)>`, etc.) submitted via the dashboard message field and the registration name field, asserting the raw payload is **never reflected unescaped** in the rendered HTML (protection provided naturally by Jinja2's autoescaping).
- Also explicitly checks that while the payload is stored raw in the database (expected — escaping is a rendering-time concern, not a storage-time concern), it always comes back escaped when rendered on the dashboard.

This suite demonstrates that the developer is verifying Flask/SQLAlchemy/Jinja2's built-in protections hold under adversarial input, rather than assuming they do.

## 9. Frontend

### Templates (Jinja2, in `scripts/templates/`)
- **`login.html`** — sign-in form plus a "Continue as Guest" option and a link to registration.
- **`register.html`** — sign-up form (email, first/last name, password + confirmation, 6-character minimum enforced both client-side via the `required` attribute and server-side in `app.py`).
- **`dashboard.html`** — two-column layout: message analyzer form + live result/feedback panel on one side, and a filterable/sortable/paginated history table below.
- **`analytics.html`** — scope selector (`all` / `mine`), summary cards (total / ham / not-ham counts), and two Chart.js bar charts (classification breakdown, feedback accuracy) with per-chart JPG/PDF export buttons powered by `jsPDF`.

### Styling (`static/style.css`)
A single dark-themed stylesheet using CSS custom properties (`--bg-dark`, `--accent`, etc.), covering:
- Auth forms and cards
- Flash message alert variants (`success`, `danger`, `warning`, `info`)
- Color-coded result boxes for `ham` / `spam` / `smishing`
- The dashboard's responsive analyzer + history layout, including a mobile breakpoint at 640px that stacks the analyzer grid and full-width buttons.

## 10. Running the Application

```bash
# 1. Clone the repository
git clone https://github.com/M3T1X1/Anti_Spam_Classifier.git
cd Anti_Spam_Classifier

# 2. (Recommended) create a virtual environment
python3 -m venv venv
source venv/bin/activate      # Linux / macOS
venv\Scripts\activate         # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. (Only if the trained model isn't already included)
#    Train the DistilBERT classifier — run from inside scripts/
cd scripts
python data_augmentation.py     # regenerates dataset_augmented.csv, if needed
python pipline_setup.py         # fine-tunes DistilBERT, saves to ../distilbert_spam_model
cd ..

# 5. Run the app
python3 run.py
```

`run.py` will, in order:
1. Run the full pytest suite (`tests/ -v`) — aborts with an error if anything fails.
2. Create all database tables (`db.create_all()`).
3. Seed demo users/messages (`seed.seed()`).
4. Start the Flask development server (`debug=True`, default `http://127.0.0.1:5000`).

To reset all stored data without restarting from scratch:

```bash
python scripts/reset_db.py
```

## 11. Security & Production Notes

- **Hardcoded secret key** (`app.secret_key = 'your-secret-key-change-this'`) must be replaced with a securely generated random value (e.g. loaded from an environment variable) before any real deployment.
- **`debug=True`** in `app.run(...)` should be disabled in production, as Flask's debugger can expose an interactive code execution console if an unhandled exception occurs.
- Tests confirm resistance to SQL injection (via SQLAlchemy's parameterized queries) and XSS (via Jinja2 autoescaping), but this relies on **not** introducing raw SQL strings or `| safe` filters elsewhere in the codebase going forward.
- The comment `# to be deleted when deploying` next to the automatic test run in `run.py` confirms the author is aware this pattern is a development-time convenience, not something intended for a production entry point.

## 12. License

The project is released under the **MIT License**:

```
MIT License
Copyright (c) 2026 Kacper Dusza
```

The MIT License permits free use, copying, modification, and distribution of the code, provided the original copyright and license notice is retained.

## 13. Summary

Anti_Spam_Classifier is a complete, self-contained SMS/message classification system combining:
- A **fine-tuned DistilBERT** transformer for 3-class text classification (ham / spam / smishing), trained on a sentence-augmented dataset of ~16k examples.
- A **Flask web application** with full authentication, a live analyzer, a shared/paginated message history, per-prediction user feedback, and a Chart.js-powered analytics dashboard with export capability.
- A **SQLite** persistence layer (`User`, `Message`, and a reserved `Plot` model) accessed through SQLAlchemy.
- A genuinely thorough **pytest suite**, including dedicated SQL-injection and XSS regression tests, that gates every application startup.

The codebase is clearly iterative/educational in places (hardcoded secret key, tests run at startup, relative script paths), but demonstrates an unusually complete loop from data augmentation → model training → deployment → automated security testing for a project of this scope.

---

*This documentation was generated from the project's publicly available source files (`run.py`, `requirements.txt`, `scripts/app.py`, `scripts/data_augmentation.py`, `scripts/pipline_setup.py`, `scripts/reset_db.py`, `scripts/seed.py`, the test suite, HTML templates, and `style.css`), plus a direct inspection of `dataset_augmented.csv`. The `database/models.py` and `database/db.py` source files were not directly available; their structure above is inferred from how they are imported and used elsewhere in the code. If the repository changes, re-verify against the current source.*
