# v20260309-1
"""
WSGI entry point. Creates the Flask application instance.

Used by:
  - run_waitress.py (production via IIS)
  - flask run (development)
"""
import os
import sys

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

from app import create_app

app = create_app()
