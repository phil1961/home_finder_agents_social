# v20260309-1
"""
Real-Time Real-Estate Data (openwebninja) API smoke test.
Run from project root: python test_zillow_api.py
"""
import json, os, sys, time
import requests
from dotenv import load_dotenv

load_dotenv()

HOST = "real-time-real-estate-data.p.rapidapi.com"
BASE = f"https://{HOST}"
KEY  = os.environ.get("RAPIDAPI_KEY", "")
if not KEY:
    print("ERROR: RAPIDAPI_KEY not set in .env"); sys.exit(1)

HEADERS = {"x-rapidapi-host": HOST, "x-rapidapi-key": KEY}

def show(r):
    print(f"  URL    : {r.url}")
    print(f"  Status : {r.status_code}")
    try:    print(f"  Body   : {json.dumps(r.json())[:600]}")
    except: print(f"  Body   : {r.text[:600]}")

# ── Test 1: Search ────────────────────────────────────────────────────────────
print("\n── Test 1: search (Charleston, SC 29407) ──")
r1 = requests.get(f"{BASE}/search", headers=HEADERS, params={
    "location":     "Charleston, SC 29407",
    "home_status":  "FOR_SALE",
    "home_type":    "HOUSES",
    "sort":         "DEFAULT",
    "listing_type": "BY_AGENT",
    "page":         1,
}, timeout=30)
show(r1)

listings = []
if r1.status_code == 200:
    body = r1.json()
    # Inspect top-level structure
    print(f"  top-level keys : {list(body.keys()) if isinstance(body, dict) else type(body)}")
    if isinstance(body, dict):
        data = body.get("data") or body.get("results") or body.get("properties") or []
        if isinstance(data, dict):
            listings = data.get("results") or data.get("properties") or data.get("home_search", {}).get("results") or []
        elif isinstance(data, list):
            listings = data
    elif isinstance(body, list):
        listings = body

    print(f"  listings found : {len(listings)}")
    if listings:
        first = listings[0]
        print(f"  first keys     : {list(first.keys())}")
        zpid = first.get("zpid") or first.get("property_id") or first.get("id") or ""
        addr = first.get("address") or first.get("full_address") or first.get("streetAddress") or ""
        price = first.get("price") or first.get("list_price") or first.get("listPrice") or ""
        print(f"  zpid/id        : {zpid}")
        print(f"  address        : {addr}")
        print(f"  price          : {price}")

time.sleep(1)

# ── Test 2: Property Details ──────────────────────────────────────────────────
print("\n── Test 2: property details ──")
# Use a known Charleston zpid from earlier logs; also try property_id
detail_params_variants = [
    {"zpid": "10863116"},
    {"property_id": "10863116"},
    {"zpid": "10863116", "address": "1451 Ravens Bluff Rd, Johns Island, SC 29455"},
]
# If search worked, use the real first result
if listings:
    first = listings[0]
    zpid = str(first.get("zpid") or first.get("property_id") or first.get("id") or "")
    addr = str(first.get("address") or first.get("full_address") or "")
    if zpid:
        detail_params_variants.insert(0, {"zpid": zpid, "address": addr})

for params in detail_params_variants:
    print(f"\n  params: {params}")
    r2 = requests.get(f"{BASE}/property-details", headers=HEADERS, params=params, timeout=30)
    show(r2)
    if r2.status_code == 200:
        body2 = r2.json()
        raw = body2.get("data") or {}
        if raw:
            desc = raw.get("description") or raw.get("overview") or ""
            print(f"  ✓ data present")
            print(f"    keys        : {list(raw.keys())[:15]}")
            print(f"    yearBuilt   : {raw.get('yearBuilt')}")
            print(f"    description : {desc[:150]!r}" if desc else "    description : (empty)")
            break
    time.sleep(0.8)
