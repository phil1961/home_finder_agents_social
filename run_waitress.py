# ─────────────────────────────────────────────
# File: run_waitress.py
# App Version: 2026.03.13 | File Version: 1.0.0
# Last Modified: 2026-03-13
# ─────────────────────────────────────────────
"""
Waitress launcher for IIS HttpPlatformHandler.

IIS calls:  python.exe run_waitress.py --port=XXXX

Waitress's url_prefix parameter handles the /home_finder_agents_social prefix:
  - Strips /home_finder_agents_social from PATH_INFO so Flask sees /dashboard
  - Sets SCRIPT_NAME so url_for() generates /home_finder_agents_social/dashboard

Local test:
  python run_waitress.py --port=8080
  Then open: http://localhost:8080/home_finder_agents_social/
"""
import os
import sys

# Ensure project root is on Python's path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Parse --port from command line (IIS passes --port=%HTTP_PLATFORM_PORT%)
port = 8080
for arg in sys.argv[1:]:
    if arg.startswith("--port="):
        port = int(arg.split("=", 1)[1])

# Load environment
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

# Create the Flask app
from wsgi import app

# Serve with waitress
from waitress import serve

print(f"HomeFinder Social starting on port {port} with prefix /home_finder_agents_social")
serve(
    app,
    host="127.0.0.1",
    port=port,
    threads=4,
    url_prefix="/home_finder_agents_social",
    url_scheme="https",
)
