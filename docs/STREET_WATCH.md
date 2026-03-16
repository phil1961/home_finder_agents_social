# HomeFinder — Street Watch Feature Guide

**Version:** 2026.03.12
**Last Updated:** 2026-03-13

---

## Overview

Street Watch lets authenticated users monitor specific streets for real estate activity. When the nightly pipeline detects a new listing, price drop, or status change on a watched street, the user receives an email alert.

---

## How It Works

### 1. User Creates a Watch

Two entry points:

**From a listing detail page:**
- The street name is auto-extracted from the listing address
- One-click "Watch This Street" button in the sidebar
- Zip code and street are pre-filled

**From the Watch management page (`/watch`):**
- Select a zip code from the site's supported zips
- Type a street name — Geoapify autocomplete suggests matches
- Click "+" to add the watch

### 2. Street Name Normalization

All street names are normalized for consistent matching:

```
"1000 Oak Drive, Charleston, SC 29407"
  → strip house number: "Oak Drive"
  → normalize suffix:   "OAK DR" (stored)
  → display version:    "Oak Dr" (shown to user)
```

**Suffix map** (examples):
| Input | Normalized |
|-------|-----------|
| Drive, Dr | DR |
| Street, St | ST |
| Road, Rd | RD |
| Boulevard, Blvd | BLVD |
| Lane, Ln | LN |
| Court, Ct | CT |
| Avenue, Ave | AVE |
| Circle, Cir | CIR |

### 3. Nightly Pipeline Detection

During the listing upsert phase, the pipeline tracks three event types:

| Event | Trigger | Example |
|-------|---------|---------|
| `new_listing` | Listing ID not previously in DB | New house listed on Oak Dr |
| `price_drop` | `price < previous_price` | Price reduced from $350K to $325K |
| `back_on_market` | Status changed back to `active` | Previously delisted house relisted |

### 4. Watch Matching

After the pipeline commits, events are matched against active watches:

```
Event: new_listing on "OAK DR" in zip 29407
  → Find all StreetWatch where street_name="OAK DR"
    AND zip_code="29407" AND is_active=True
  → Create StreetWatchAlert for each match
```

### 5. Email Digest

Pending alerts (where `emailed_at IS NULL`) are grouped by email and sent as a single HTML digest:

- Purple gradient header
- Per-alert cards with photo thumbnail, price, beds/baths/sqft, deal score
- Alert type badges (New Listing, Price Drop, Back on Market)
- Direct link to listing detail page
- One-click unsubscribe link

---

## Data Model

### StreetWatch

| Field | Type | Description |
|-------|------|-------------|
| id | Integer PK | |
| email | String | Notification email (from user account) |
| user_id | FK → User | Linked to account (nullable for legacy) |
| street_name | String | Normalized uppercase (e.g., "OAK DR") |
| zip_code | String | 5-digit zip |
| label | String | Display version (e.g., "Oak Dr") |
| is_active | Boolean | Active or deactivated |
| unsubscribe_token | String (unique) | Secure token for email unsubscribe |
| created_at | DateTime | |
| last_alerted_at | DateTime | |

**Unique constraint:** `(email, street_name, zip_code)` — prevents duplicate watches.

### StreetWatchAlert

| Field | Type | Description |
|-------|------|-------------|
| id | Integer PK | |
| watch_id | FK → StreetWatch | |
| listing_id | FK → Listing | |
| alert_type | String | `new_listing`\|`price_drop`\|`back_on_market` |
| detail_json | Text | JSON with event details |
| created_at | DateTime | |
| emailed_at | DateTime | NULL = pending, set after email sent |

**Unique constraint:** `(watch_id, listing_id, alert_type)` — idempotent alert creation.

---

## Geoapify Integration

Street autocomplete uses the Geoapify Address Autocomplete API, called directly from the browser (no server proxy):

```
GET https://api.geoapify.com/v1/geocode/autocomplete
  ?text=Win 21228
  &type=street
  &filter=circle:-76.7284,39.2721,25000
  &format=json
  &limit=10
  &apiKey=<key>
```

**Optimizations:**
- **Circle filter:** 25km radius around the site's map center — limits results to the local area
- **Client-side SITE_ZIPS filter:** Results are additionally filtered in JavaScript to only show streets in the site's registered zip codes
- **Deduplication:** Normalized street + zip combination used as key

**Fallback:** When no `GEOAPIFY_KEY` is configured, autocomplete searches the local listing database for matching street names.

**Free tier:** 90,000 requests/month (no credit card required at geoapify.com).

---

## Authentication

Street Watch requires a registered, verified account. Guests visiting the `/watch` page see a modal explaining:
- A free account is needed
- A verification email will confirm their address
- Link to the registration page

The verification email includes a link directly to the Watch page for easy onboarding.

---

## Unsubscribe

Every watch has a unique `unsubscribe_token` (generated via `secrets.token_urlsafe(32)`).

- Every alert email includes a one-click unsubscribe link
- Clicking the link deactivates the specific watch (not all watches)
- No authentication required for unsubscribe (token-based)

---

## Reactivation

If a user removes a watch and later re-adds the same street + zip:
- The existing deactivated record is found (unique constraint)
- `is_active` is set back to `True`
- A new `unsubscribe_token` is generated
- No duplicate row is created

---

## Pipeline Integration

Watch processing is non-blocking:

```python
try:
    alert_count = check_watches_after_pipeline(watch_events, site_key)
    digest_count = send_watch_digests(site_key)
except Exception:
    log.warning("Watch processing failed — pipeline continues")
```

A failure in watch matching or email sending never breaks the main fetch/score cycle.
