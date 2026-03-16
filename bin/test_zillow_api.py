# v20260309-1
"""
Zillow (us-property-data) API smoke test — corrected params.
Run from project root: python test_zillow_api.py
"""
import json
import os
import sys
import time

import requests
from dotenv import load_dotenv

load_dotenv()

HOST = "us-property-data.p.rapidapi.com"
BASE = f"https://{HOST}/api/v1"
KEY  = os.environ.get("RAPIDAPI_KEY", "")

if not KEY:
    print("ERROR: RAPIDAPI_KEY not set in .env")
    sys.exit(1)

HEADERS = {
    "x-rapidapi-host": HOST,
    "x-rapidapi-key":  KEY,
}

def show(label, r):
    print(f"  URL    : {r.url}")
    print(f"  Status : {r.status_code}")
    try:
        print(f"  Body   : {json.dumps(r.json())[:400]}")
    except Exception:
        print(f"  Body   : {r.text[:400]}")

# ── Test 1: search/by-location with corrected params ─────────────────────────
print("\n── Test 1: search/by-location (corrected params) ──")
r1 = requests.get(
    f"{BASE}/search/by-location",
    headers=HEADERS,
    params={
        "location":       "29407",
        "page":           1,
        "listing_status": "for_sale",
        "sort_by":        "globalrelevanceex",
    },
    timeout=30,
)
show("by-location", r1)

listings = []
if r1.status_code == 200:
    body = r1.json()
    if isinstance(body, list):
        listings = body
    elif isinstance(body, dict):
        listings = (body.get("data") or {}).get("results") or body.get("results") or []
    print(f"  Listings found: {len(listings)}")
    if listings:
        first = listings[0]
        print(f"  First result keys : {list(first.keys())}")
        print(f"  zpid              : {first.get('zpid')}")
        print(f"  address           : {first.get('address') or first.get('streetAddress')}")
        print(f"  price             : {first.get('price') or first.get('listPrice')}")

time.sleep(1)  # respect rate limit

# ── Test 2: property/detail with address param ────────────────────────────────
print("\n── Test 2: property/detail (with address param) ──")
zpid    = str(listings[0].get("zpid", "")) if listings else "58916071"
address = str(listings[0].get("address") or listings[0].get("streetAddress") or "") if listings else ""

r2 = requests.get(
    f"{BASE}/property/detail",
    headers=HEADERS,
    params={
        "zpid":                  zpid,
        "address":               address,
        "include_extended_info": "false",
    },
    timeout=30,
)
show("property/detail", r2)

if r2.status_code == 200:
    body2 = r2.json()
    raw   = body2.get("data", {}) or {}
    print(f"  success     : {body2.get('success')}")
    print(f"  year_built  : {raw.get('yearBuilt')}")
    desc  = raw.get("description") or raw.get("overview") or ""
    print(f"  description : {desc[:150]!r}" if desc else "  description : (empty)")
    reso  = raw.get("resoFacts") or {}
    print(f"  resoFacts keys: {list(reso.keys())[:12]}")
