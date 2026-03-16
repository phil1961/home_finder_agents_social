# v20260309-1
"""
Manually run the scraper pipeline to populate listings NOW.

Usage (from your home_finder_agents directory):
    python fetch_now.py

This will:
  1. Load your .env config (RAPIDAPI_KEY, etc.)
  2. Query Zillow and Realtor.com for matching properties
  3. Upsert them into your database
  4. Score each listing

Run this after setting up your .env to get your first batch of listings.
"""
import logging
import sys

from dotenv import load_dotenv
load_dotenv()

import os

# Pre-flight checks
key = os.environ.get("RAPIDAPI_KEY", "")
if not key:
    print("ERROR: RAPIDAPI_KEY is not set.")
    print("Make sure your .env file exists and contains RAPIDAPI_KEY=your-key")
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("fetch_now")

from app import create_app
from app.scraper.pipeline import run_pipeline

app = create_app()

print()
print("=" * 60)
print("  HomeFinder — Manual Fetch")
print("=" * 60)
print(f"  RAPIDAPI_KEY: {key[:8]}...{key[-4:]}")
print()

with app.app_context():
    from config import TARGET_AREAS, MAX_PRICE, MIN_BEDS, MIN_BATHS
    all_zips = set()
    for area, info in TARGET_AREAS.items():
        zips = info.get("zip_codes", [])
        all_zips.update(zips)
        print(f"  {area}: zips {zips}")
    print(f"  Filters: ≤${MAX_PRICE:,} | ≥{MIN_BEDS}BR | ≥{MIN_BATHS}BA")
    print()
    print("Fetching from Zillow and Realtor.com...")
    print("(This may take 30-60 seconds depending on how many zip codes)")
    print()

    count = run_pipeline(app)

    print()
    if count > 0:
        print(f"Done! {count} listings loaded into the database.")
        print("Start the app with 'python run.py' and check your dashboard.")
    else:
        print("No listings were returned.")
        print()
        print("Troubleshooting:")
        print("  1. Verify your RAPIDAPI_KEY is correct")
        print("  2. Make sure you're subscribed to BOTH APIs on RapidAPI:")
        print("     - 'Realty in US' by apidojo")
        print("     - 'Zillow-com1' by apimaker")
        print("  3. Check the log output above for specific API errors")
