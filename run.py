# v20260309-1
"""Run the HomeFinder application."""
import logging
import os

from dotenv import load_dotenv
load_dotenv()

from app import create_app
from app.scraper.scheduler import start_scheduler

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logging.getLogger('app.scraper.zillow').setLevel(logging.DEBUG)

app = create_app()

# Start the background scheduler (fetches every FETCH_INTERVAL_HOURS)
# Only start in the main process (avoid double-start with Flask reloader)
if os.environ.get("WERKZEUG_RUN_MAIN") == "true" or not app.debug:
    start_scheduler(app)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
