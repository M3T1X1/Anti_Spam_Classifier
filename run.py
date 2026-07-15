#!/usr/bin/env python3
"""
Run the Flask application
Usage: python3 run.py
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import and run app
from scripts.app import app

if __name__ == "__main__":
    app.run(debug=True)
