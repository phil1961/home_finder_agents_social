# DEPLOYMENT LOCATION: /home/homefinder/home_finder_agents_social/wsgi.py
# Gathered by gather_configs.sh on 2026-03-21 11:42:20

# ─────────────────────────────────────────────
# File: wsgi.py
# App Version: 2026.03.15 | File Version: 1.1.0
# Last Modified: 2026-03-15
# ─────────────────────────────────────────────
"""
WSGI entry point. Creates the Flask application instance.

Used by:
  - run_waitress.py (production via IIS on Windows)
  - gunicorn wsgi:app (production via Nginx on Linux)
  - flask run (development)
"""
import os
import sys

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

from app import create_app


class PrefixMiddleware:
    """WSGI middleware that strips a URL prefix from PATH_INFO.

    Gunicorn doesn't have Waitress's url_prefix parameter, so this
    middleware replicates that behavior for Nginx reverse proxy setups
    where the app is mounted at /home_finder_agents_social/.

    Nginx config:
        location /home_finder_agents_social/ {
            proxy_pass http://127.0.0.1:8080/home_finder_agents_social/;
        }
    """
    def __init__(self, app, prefix="/home_finder_agents_social"):
        self.app = app
        self.prefix = prefix

    def __call__(self, environ, start_response):
        path = environ.get("PATH_INFO", "")
        if path.startswith(self.prefix):
            environ["PATH_INFO"] = path[len(self.prefix):] or "/"
            environ["SCRIPT_NAME"] = self.prefix
        return self.app(environ, start_response)


app = create_app()

# Apply prefix middleware when running under Gunicorn (not Waitress/IIS)
# Waitress handles the prefix via url_prefix in run_waitress.py
if os.environ.get("GUNICORN_WORKER") or os.environ.get("USE_PREFIX_MIDDLEWARE"):
    app.wsgi_app = PrefixMiddleware(app.wsgi_app)
