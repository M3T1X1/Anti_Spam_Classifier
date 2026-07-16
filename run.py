#!/usr/bin/env python3
"""
Run the Flask application
Usage: python3 run.py
"""
import sys
from pathlib import Path
import subprocess
from database import db
from scripts import seed

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from scripts.app import app

def run_tests(): # to be deleted when deploying
    result = subprocess.run([sys.executable, "-m", "pytest", "tests/", "-v"], cwd=str(project_root))
    if result.returncode != 0:
        print("ERROR: tests failed")
        sys.exit(1)
    else:
        print("All tests passed")

if __name__ == "__main__":
    run_tests()

    with app.app_context():
        db.create_all()
        seed.seed()

    app.run(debug=False, use_reloader=False)
