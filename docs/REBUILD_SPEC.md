<!--
  File: docs/REBUILD_SPEC.md
  App Version: 1.1.0 | File Version: 1.1.0
  Last Modified: 2026-03-17
-->

# HomeFinder Social — Comprehensive Rebuild Specification

**Version:** 1.1.0
**Date:** 2026-03-17
**Purpose:** Complete feature specification for rebuilding HomeFinder Social from the ground up. This document captures every user-facing feature, backend service, data model, and integration point so a developer (human or AI) can reconstruct the entire application with minimal guidance.

---

## Table of Contents

1. [System Identity & Goals](#1-system-identity--goals)
2. [Architecture Overview](#2-architecture-overview)
3. [Multi-Tenant Routing](#3-multi-tenant-routing)
4. [Database Schema](#4-database-schema)
5. [User Roles & Permissions](#5-user-roles--permissions)
6. [Authentication & Account Management](#6-authentication--account-management)
7. [The Data Pipeline](#7-the-data-pipeline)
8. [The 18-Factor Scoring Engine](#8-the-18-factor-scoring-engine)
9. [Dashboard & Listing Browsing](#9-dashboard--listing-browsing)
10. [Listing Detail & Enrichment](#10-listing-detail--enrichment)
11. [Preferences & Scoring Customization](#11-preferences--scoring-customization)
12. [AI Deal Analyst (Claude Integration)](#12-ai-deal-analyst-claude-integration)
13. [Map View](#13-map-view)
14. [Tour Planner](#14-tour-planner)
15. [Street Watch](#15-street-watch)
16. [Agent Features](#16-agent-features)
17. [Owner Administration](#17-owner-administration)
18. [Master Site Management](#18-master-site-management)
19. [Social Features](#19-social-features)
20. [Billing & Quota System](#20-billing--quota-system)
21. [Email System](#21-email-system)
22. [Documentation System](#22-documentation-system)
23. [Frontend Architecture](#23-frontend-architecture)
24. [Static Assets & PWA](#24-static-assets--pwa)
25. [Configuration & Environment](#25-configuration--environment)
26. [Error Handling & Logging](#26-error-handling--logging)
27. [Testing](#27-testing)
28. [Deployment](#28-deployment)
29. [Improvement Recommendations](#29-improvement-recommendations)

---

## 1. System Identity & Goals

**HomeFinder Social** is a multi-tenant web application for real estate listing discovery. It serves **buyers** — not sellers, not agents. Every feature, every AI prompt, every scoring algorithm is designed to give buyers an honest, adversarial edge.

### Core Value Propositions

- **18-factor deal scoring** — every listing gets a composite score (0-100) based on price, features, location, market dynamics, and user-customized importance weights
- **AI-powered deal analysis** — Claude provides brutally honest assessments: strengths, red flags, negotiation leverage, and dollar-specific opening offers
- **Multi-market support** — each market (Charleston SC, Bath WV, Dover DE, etc.) runs as an isolated tenant with its own database, zip codes, and configuration
- **Social layer** — sharing, reactions, collections, referrals, points/leaderboard, friend-submitted listings
- **Role hierarchy** — master, owner, agent, principal, client, guest — each with appropriate capabilities and restrictions
- **Zero-login browsing** — guests can browse, flag listings, run AI analysis, and share — all session-persisted without an account

### Live URL Pattern

```
https://www.toughguycomputing.com/home_finder_agents_social/site/<site_key>/
```

---

## 2. Architecture Overview

### Technology Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.11+ |
| Framework | Flask 3.x with app factory pattern |
| ORM | Flask-SQLAlchemy (custom multi-tenant subclass) |
| Database | SQLite (one per tenant + one registry) |
| Auth | Flask-Login + bcrypt |
| Email | Flask-Mail (SMTP) |
| AI | Anthropic Claude API (Sonnet) |
| Listing Data | RapidAPI (Zillow "Real-Time Real-Estate Data" + Realtor "Realty In US") |
| Maps | Leaflet.js + OpenStreetMap tiles |
| Geocoding | Nominatim (free) + Google Maps (fallback) |
| CSS Framework | Bootstrap 5 |
| Icons | Bootstrap Icons + Twemoji |
| Server | Waitress (local) / IIS HttpPlatformHandler (production) |
| Scheduler | Windows Task Scheduler (production) |

### Project Structure

```
/
├── app/
│   ├── __init__.py              # Flask factory, WSGI middleware, session routing
│   ├── models.py                # 14 core ORM models
│   ├── models_social.py         # 9 social ORM models
│   ├── migrations.py            # Idempotent schema migrations
│   ├── routes/
│   │   ├── auth.py              # 13 routes — registration, login, masquerade
│   │   ├── dashboard_helpers.py # Blueprint registration hub
│   │   ├── listings.py          # 7 routes — dashboard, detail, flag, note, enrich
│   │   ├── admin_routes.py      # 17 routes — metrics, prompts, users, billing, feedback
│   │   ├── agent_routes.py      # 11 routes — client roster, branding, friend listings
│   │   ├── preferences_routes.py# 8 routes — scoring weights, landmarks, areas, help level, power mode
│   │   ├── tour_routes.py       # 6 routes — itinerary, contact agent, help pages
│   │   ├── ai_routes.py         # 3 routes — deal/portfolio/preferences analysis
│   │   ├── watch_routes.py      # 5 routes — street watch CRUD, alerts
│   │   ├── social.py            # 23 routes — sharing, collections, referrals, points
│   │   ├── site_manager.py      # 7 routes — master site CRUD
│   │   └── docs.py              # 4 routes — documentation serving
│   ├── services/
│   │   ├── registry.py          # Registry.db CRUD (raw sqlite3)
│   │   ├── deal_analyst.py      # Claude API wrapper
│   │   ├── ai_context.py        # Prompt-building (pure functions, no I/O)
│   │   ├── billing.py           # Plan tiers, quota checks, budget alerts
│   │   ├── points.py            # Gamification: awards, daily cap, leaderboard
│   │   ├── street_watch.py      # Watch creation, alerts, email digests
│   │   ├── social_digest.py     # Weekly activity email
│   │   └── place_geocoder.py    # Geocoding fallback
│   ├── scraper/
│   │   ├── pipeline.py          # Full fetch→dedup→upsert→score workflow
│   │   ├── zillow.py            # Zillow API client + normalizer
│   │   ├── realtor.py           # Realtor API client + normalizer
│   │   ├── scorer.py            # 18-factor scoring engine
│   │   ├── geocoder.py          # Coordinate resolution
│   │   └── scheduler.py         # Legacy APScheduler (replaced by Task Scheduler)
│   ├── templates/               # ~78 Jinja2 templates
│   │   ├── base.html            # Master layout
│   │   ├── landing.html         # Site chooser
│   │   ├── auth/                # 12 templates
│   │   ├── dashboard/           # 34 templates (includes admin_feedback.html)
│   │   ├── social/              # 14 templates
│   │   └── email/               # 5 templates
│   └── static/
│       ├── css/style.css        # Single stylesheet
│       ├── js/
│       │   ├── preferences.js   # Scoring sliders, AJAX form save
│       │   ├── landmarks.js     # User/admin landmark CRUD with map
│       │   ├── help-hints.js    # Help level system: tooltips + inline hints
│       │   └── site-manager.js  # Map/location/zip picker modals
│       ├── sw.js                # Service worker (PWA)
│       ├── manifest.json        # PWA manifest
│       ├── icons/               # 192px + 512px app icons
│       └── uploads/             # Friend listing photo uploads
├── config.py                    # All configuration constants
├── pipeline.py                  # CLI entry point
├── wsgi.py                      # WSGI entry (IIS/Gunicorn)
├── run_waitress.py              # Local dev server
├── instance/
│   ├── registry.db              # Master site registry
│   └── *.db                     # Per-site databases
├── tests/                       # 84 integration tests (7 files)
├── docs/                        # Markdown documentation
└── bin/
    └── scheduled_pipeline.py    # Windows Task Scheduler entry point
```

### Blueprint Layout

| Blueprint | URL Prefix | Purpose |
|-----------|-----------|---------|
| `auth_bp` | `/auth` | Authentication, registration, masquerade |
| `dashboard_bp` | `/` (root) | All buyer/owner/agent routes, admin, preferences |
| `social_bp` | `/social` | Sharing, collections, reactions, referrals, points |
| `site_manager_bp` | `/admin/sites` | Master-only site CRUD |
| `docs_bp` | `/docs` | Documentation serving |

**Total route count:** ~111 endpoints across 12 route files.

---

## 3. Multi-Tenant Routing

This is the most architecturally important piece. Every request must resolve to the correct site and database.

### URL Structure

```
/home_finder_agents_social/site/<site_key>/<route>
```

Example: `/home_finder_agents_social/site/charleston/preferences`

### Three-Layer Routing

**Layer 1: WSGI Middleware (`SitePathMiddleware`)**

Runs before Flask sees the request. Extracts site key from the URL path, strips it, and passes it as an HTTP header:

- Input: `PATH_INFO = /site/charleston/preferences`
- Output: `PATH_INFO = /preferences`, `HTTP_X_HOMEFINDER_SITE = charleston`

This lets all route handlers be written without site awareness — they just see `/preferences`.

**Layer 2: Before-Request Hook (`select_site()`)**

Reads the `HTTP_X_HOMEFINDER_SITE` header, looks up the site in `registry.db`, and binds:
- `g.site` — dict of registry metadata (site_key, display_name, db_path, map config, zip codes, landmarks, billing plan)
- `g.site_engine` — SQLAlchemy engine pointing at the correct per-site SQLite file

On first access to a new site, also runs `db.create_all()` + migrations.

**Layer 3: Session Routing (`_SiteRoutedSession`)**

Custom SQLAlchemy session wrapper. Every call to `db.session.query(...)` is transparently routed to `g.site_engine`. No route handler ever needs to specify which database to use.

### Engine Cache

Engines are cached in a thread-safe dict keyed by absolute DB path. Created on first access, reused for all subsequent requests to the same site.

### Template URL Helper: `site_url()`

**Critical convention:** Templates must use `site_url('blueprint.route')` instead of `url_for()`. This injects the `/site/<key>/` prefix back into generated URLs.

Exceptions:
- `url_for('static', filename='...')` — static assets are site-agnostic
- `url_for('site_manager.*')` — site manager is global

---

## 4. Database Schema

### 4.1 Registry Database (`instance/registry.db`)

Raw sqlite3 (not ORM-managed). Single table `sites`:

| Column | Type | Purpose |
|--------|------|---------|
| `id` | INTEGER PK | Auto-increment |
| `site_key` | TEXT UNIQUE | URL slug: "charleston", "bathwv" |
| `display_name` | TEXT | Human label: "Charleston, SC" |
| `db_path` | TEXT | Relative path: "instance/charlestonsc.db" |
| `map_center_lat` | REAL | Map center latitude |
| `map_center_lon` | REAL | Map center longitude |
| `map_zoom` | INTEGER | Default zoom level |
| `map_bounds_json` | TEXT | JSON: `[[sw_lat, sw_lon], [ne_lat, ne_lon]]` |
| `zip_codes_json` | TEXT | JSON array of zip codes for pipeline |
| `target_areas_json` | TEXT | JSON: `{"Area Name": ["29401", ...]}` |
| `landmarks_json` | TEXT | JSON array of POI landmarks |
| `active` | BOOLEAN | Whether site is active |
| `owner_email` | TEXT | Site owner's email |
| `pipeline_last_run` | DATETIME | Last successful pipeline run |
| `listing_count` | INTEGER | Cached active listing count |
| `scheduler_paused` | BOOLEAN | Pipeline manually paused |
| `scheduler_locked` | BOOLEAN | Master-only scheduler disable |
| `max_fetches_per_run` | INTEGER | Pipeline listing cap |
| `billing_plan` | TEXT | free / basic / pro / unlimited |
| `monthly_budget` | REAL | USD spend cap |
| `monthly_limit_ai` | INTEGER | Max AI calls/month |
| `monthly_limit_fetch` | INTEGER | Max fetch calls/month |
| `billing_email` | TEXT | Alert recipient |
| `billing_cycle_start` | INTEGER | Day 1-28 |
| `created_at` | DATETIME | Site creation |

### 4.2 Per-Site Database Models

Each site gets an independent SQLite database with identical schema. All managed via SQLAlchemy ORM.

#### Users

| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER PK | |
| `email` | STRING(254) | NOT unique — same email can have master+owner+agent+user accounts |
| `username` | STRING(40) | UNIQUE |
| `password_hash` | STRING(256) | bcrypt |
| `is_verified` | BOOLEAN | Email verified |
| `is_suspended` | BOOLEAN | Account suspended |
| `suspended_reason` | STRING(200) | |
| `role` | STRING(20) | master / owner / agent / principal / client |
| `agent_id` | INTEGER FK→agent_profiles | For principals — their managing agent |
| `preferences_json` | TEXT | JSON blob of all user preferences (see Section 11) |
| `created_at` | DATETIME | |
| `last_login` | DATETIME | |

#### Listings

| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER PK | |
| `source` | STRING(20) | "zillow", "realtor", "agent", "friend" |
| `source_id` | STRING(100) UNIQUE | External ID for dedup |
| `url` | TEXT | Link to original listing |
| `status` | STRING(20) | active / pending / sold / inactive |
| `address` | TEXT | Full street address |
| `city` | STRING(80) | |
| `zip_code` | STRING(10) | |
| `area_name` | STRING(80) | Target area label |
| `place_name` | STRING(100) | Census place name |
| `price` | INTEGER | List price |
| `beds` | INTEGER | |
| `baths` | FLOAT | |
| `sqft` | INTEGER | Living area |
| `lot_sqft` | INTEGER | Lot size |
| `year_built` | INTEGER | |
| `latitude` | FLOAT | |
| `longitude` | FLOAT | |
| `stories` | INTEGER | |
| `is_single_story` | BOOLEAN | |
| `hoa_monthly` | FLOAT | |
| `list_date` | DATETIME | |
| `days_on_market` | INTEGER | |
| `property_tax_annual` | FLOAT | |
| `has_community_pool` | BOOLEAN | |
| `nearest_hospital_miles` | FLOAT | |
| `nearest_grocery_miles` | FLOAT | |
| `walkability_score` | FLOAT | |
| `price_change_pct` | FLOAT | |
| `has_garage` | BOOLEAN | |
| `has_porch` | BOOLEAN | |
| `has_patio` | BOOLEAN | |
| `flood_zone` | STRING(10) | |
| `above_flood_plain` | BOOLEAN | |
| `details_json` | TEXT | Lazily-fetched enrichment data |
| `details_fetched` | BOOLEAN | |
| `photo_urls_json` | TEXT | JSON array of photo URLs |
| `price_history_json` | TEXT | JSON array of price events |
| `description` | TEXT | |
| `first_seen` | DATETIME | |
| `last_seen` | DATETIME | |

**Photo URL helpers:** The Listing model provides `photos`, `photos_large`, and `photos_original` properties that parse `photo_urls_json` and rewrite URLs for different resolutions (Zillow/Realtor CDN-specific size parameters).

#### DealScore (1:1 with Listing)

| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER PK | |
| `listing_id` | INTEGER FK UNIQUE | |
| `price_score` | FLOAT | 0-100 |
| `size_score` | FLOAT | 0-100 |
| `yard_score` | FLOAT | 0-100 |
| `feature_score` | FLOAT | 0-100 |
| `flood_score` | FLOAT | 0-100 |
| `extended_scores_json` | TEXT | JSON: 12 additional factor scores |
| `composite_score` | FLOAT | Weighted average of all 18 |
| `scored_at` | DATETIME | |

**Key method:** `compute_user_composite(user_prefs)` — recalculates composite using this specific user's importance weights. This is called on every dashboard load so each user sees personalized scores.

#### UserFlag (user + listing unique pair)

| Column | Type | Notes |
|--------|------|-------|
| `user_id` | INTEGER FK | |
| `listing_id` | INTEGER FK | |
| `flag` | STRING(20) | favorite / maybe / hide |
| `note` | TEXT | Optional |
| `flagged_at` | DATETIME | |

#### ListingNote (user + listing unique pair)

| Column | Type | Notes |
|--------|------|-------|
| `user_id` | INTEGER FK | |
| `listing_id` | INTEGER FK | |
| `note_text` | TEXT | |
| `visited` | BOOLEAN | |
| `scheduled_visit` | BOOLEAN | |
| `not_interested` | BOOLEAN | |
| `made_offer` | BOOLEAN | |
| `updated_at` | DATETIME | |

#### AgentProfile (1:1 with User)

| Column | Type | Notes |
|--------|------|-------|
| `user_id` | INTEGER FK UNIQUE | |
| `full_name` | STRING(120) | |
| `license_number` | STRING(50) | |
| `brokerage` | STRING(120) | |
| `phone` | STRING(30) | |
| `bio` | TEXT | |
| `service_areas` | TEXT | |
| `status` | STRING(20) | pending / approved / suspended |
| `brand_color` | STRING(7) | Hex color |
| `brand_logo_url` | STRING(500) | |
| `brand_icon` | STRING(50) | Bootstrap Icon key |
| `brand_tagline` | STRING(200) | |
| `brand_tagline_style` | STRING(30) | plain / italic / bold / etc. |

#### AgentClientNote, OwnerAgentNote, PromptOverride

Agent-to-client notes (with status checkboxes: pre_approved, signed_agreement, tour_scheduled, offer_submitted, active_searching), owner-to-agent notes (with checkboxes: contract_signed, background_checked, mls_verified), and per-type AI prompt overrides (agent-specific or site-wide).

#### ApiCallLog

Tracks every external API call for billing, troubleshooting, and diagnostics:

| Column | Type | Notes |
|--------|------|-------|
| `call_type` | STRING(30) | zillow, realtor, zillow_detail, realtor_detail, anthropic_deal, anthropic_portfolio, anthropic_prefs, google_places, google_geocode |
| `user_id` | INTEGER FK nullable | Null for scheduler/background |
| `site_key` | STRING(50) | |
| `zip_code` | STRING(10) | |
| `trigger` | STRING(20) | manual / scheduled |
| `success` | BOOLEAN | |
| `response_time_ms` | INTEGER | |
| `http_status` | INTEGER | |
| `results_count` | INTEGER | |
| `quota_remaining` | INTEGER | |
| `called_at` | DATETIME | |

**Cost map:** Each call_type has a cost (zillow: $0.005, anthropic_deal: $0.015, anthropic_portfolio: $0.025, etc.)

#### CachedAnalysis

Caches Claude AI results per user per listing per analysis type. Unique on `(user_id, analysis_type, listing_id)`.

#### StreetWatch + StreetWatchAlert

Street-level monitoring with email notifications. Unique on `(email, street_name, zip_code)`. Alerts tracked per `(watch_id, listing_id, alert_type)`.

### 4.3 Social Models (same per-site DB)

#### SocialShare

| Column | Type | Notes |
|--------|------|-------|
| `listing_id` | INTEGER FK nullable | |
| `collection_id` | INTEGER FK nullable | |
| `share_type` | STRING(20) | listing / collection |
| `sharer_id` | INTEGER FK nullable | Null if guest |
| `sharer_name/email` | STRING | |
| `recipient_email` | STRING(254) | |
| `recipient_user_id` | INTEGER FK nullable | Linked after registration |
| `relationship` | STRING(30) | friend / family / coworker / neighbor / client / agent |
| `message` | TEXT | Personal note |
| `share_token` | STRING(64) UNIQUE | Public URL token |
| `status` | STRING(20) | sent / viewed / clicked / replied |
| `viewed_at` / `clicked_at` | DATETIME | Engagement tracking |

#### SocialReaction

| Column | Type | Notes |
|--------|------|-------|
| `share_id` | INTEGER FK | |
| `reactor_email` | STRING(254) | |
| `reaction_type` | STRING(30) | love / interested / great_location / too_expensive / not_for_me |
| `comment` | TEXT | |

Unique on `(share_id, reactor_email)`.

#### SocialCollection + SocialCollectionItem

Curated groups of listings. Collection has title, description, share_token, is_public, share_count, view_count. Items have listing_id, note, position. Unique on `(collection_id, listing_id)`.

#### Referral

| Column | Type | Notes |
|--------|------|-------|
| `referrer_id` | INTEGER FK | |
| `referred_email` | STRING(254) | |
| `referred_user_id` | INTEGER FK nullable | Set when they register |
| `referral_code` | STRING(20) UNIQUE | |
| `status` | STRING(20) | invited / registered / active / converted |

Referral loop closes at registration when the referred user's session contains the referral code.

#### UserPoints + UserPointLog

Balance tracking (balance, lifetime_earned) and event log (delta, reason, reference_id). 7 earning actions with 50 points/day cap.

#### FriendListing

Community-submitted homes ("Add a Home"):

| Column | Type | Notes |
|--------|------|-------|
| `submitter_id/email` | | Who submitted |
| `address, city, zip_code` | | Property location |
| `price, bedrooms, bathrooms, sqft` | | Property details |
| `description` | TEXT | |
| `photos_json` | TEXT | Uploaded photo filenames |
| `relationship` | STRING(30) | my_home / friend / neighbor / family |
| `has_permission` | BOOLEAN | Owner permission to list |
| `status` | VARCHAR(20) | active / expired / removed / approved / rejected |
| `approved_by_agent_id` | INTEGER FK nullable | |
| `listing_id` | INTEGER FK nullable | Promoted Listing if approved |
| `rejection_reason` | VARCHAR(200) | |

#### Feedback

User/guest feedback submissions with sentiment tracking:

| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER PK | |
| `user_id` | INTEGER FK nullable | Null if guest |
| `email` | STRING(254) nullable | Provided by guests (optional) |
| `sentiment` | STRING(20) | "positive", "neutral", "negative" (thumbs up/meh/thumbs down) |
| `comment` | TEXT nullable | Optional free-form text |
| `page_url` | STRING(500) | Page the user was on when submitting |
| `is_read` | BOOLEAN | Default False; toggled by owner via admin |
| `created_at` | DATETIME | |

### 4.4 Schema Migrations

File: `app/migrations.py` — function `apply_all(engine)`.

**Strategy:** Check-before-alter. Each column inspected via `PRAGMA table_info()` before `ALTER TABLE ADD COLUMN`. Each table checked via `SELECT name FROM sqlite_master` before `CREATE TABLE`.

Called on:
1. App startup in `create_app()`
2. First request to each site in `select_site()`

**Rule:** Never write UPDATE/seed that modifies `role='master'` users. Only promote FROM `role='user'`.

---

## 5. User Roles & Permissions

### Hierarchy

```
master > owner > agent > principal > client > guest
```

### Role Capabilities

| Capability | Guest | Client | Principal | Agent | Owner | Master |
|-----------|-------|--------|-----------|-------|-------|--------|
| Browse listings | Y | Y | Y | Y | Y | Y |
| Flag (fav/maybe/hide) | Session | Y | Y | Y | Y | Y |
| AI deal analysis | Y | Y | Y | Y | Y | Y |
| Set preferences | Session | Y | Read-only | Y | Y | Y |
| Submit feedback | Y | Y | Y | Y | Y | Y |
| Share listings | Y | Y | Y | Y | Y | Y |
| Create collections | | Y | Y | Y | Y | Y |
| Street watch | Email-only | Y | Y | Y | Y | Y |
| View tour planner | | Y | Y | Y | Y | Y |
| Submit friend listing | | Y | Y | Y | Y | Y |
| Manage clients | | | | Y | | |
| Brand customization | | | | Y | | |
| Masquerade as clients | | | | Y | | |
| Review friend listings | | | | Y | | |
| Create listings directly | | | | Y | | |
| Agent-specific prompts | | | | Y | | |
| Review feedback | | | | | Y | Y |
| Approve/suspend agents | | | | | Y | |
| Manage users | | | | | Y | |
| Configure billing | | | | | Y | |
| Set site-wide prompts | | | | | Y | |
| Trigger pipeline | | | | Y | Y | |
| Site registry CRUD | | | | | | Y |
| Masquerade as anyone | | | | | | Y |
| Lock/unlock scheduler | | | | | | Y |
| Add zips to site | | | | | | Y |

### Role-Priority Login

When multiple accounts share the same email, login selects the highest-role account. Typing a specific username bypasses this and logs into that exact account.

### Role Switcher

Master users see a "Switch Role" dropdown listing sibling accounts (same email) with role badges. One-click masquerade to any sibling. Hidden during active masquerade.

### Masquerade

- **Agents** can masquerade as their own clients
- **Master** can masquerade as any user
- Chained: Master → Agent → Principal (original ID stored only on first hop, never overwritten)
- "End Preview" always returns to the true original user

---

## 6. Authentication & Account Management

### Routes

| Route | Method | Purpose |
|-------|--------|---------|
| `/auth/register` | GET/POST | User registration |
| `/auth/login` | GET/POST | Login (email or username) |
| `/auth/logout` | POST | Logout |
| `/auth/verify/<token>` | GET | Email verification |
| `/auth/resend-verification` | GET/POST | Request new verification email |
| `/auth/forgot-password` | GET/POST | Request password reset |
| `/auth/reset-password/<token>` | GET/POST | Reset password with token |
| `/auth/change-password` | GET/POST | Change password (logged in) |
| `/auth/close-account` | GET/POST | Permanently close account |
| `/auth/agent-signup` | POST | Agent registration (creates AgentProfile) |
| `/auth/masquerade/<user_id>` | POST | Enter masquerade |
| `/auth/end-masquerade` | GET | Exit masquerade |

### Key Behaviors

- Passwords stored as bcrypt hashes
- Verification tokens expire after 1 hour (`VERIFICATION_TOKEN_MAX_AGE`)
- Sessions persist 14 days (`PERMANENT_SESSION_LIFETIME`)
- Agent signup creates both User (role=agent) and AgentProfile (status=pending)
- Registration checks for referral code in session → closes referral loop

---

## 7. The Data Pipeline

### Entry Points

1. **CLI:** `python pipeline.py --site charleston` (fetch + dedup + score)
2. **CLI rescore:** `python pipeline.py --site charleston --rescore`
3. **Scheduled:** Windows Task Scheduler → `bin/scheduled_pipeline.py`
4. **Manual:** Owner clicks "Fetch Now" on metrics page → AJAX POST to `/fetch-now`

### Pipeline Flow

```
1. Resolve site → get zip_codes from registry
2. Fetch Zillow listings (per zip, paginated, rate-limited)
3. Fetch Realtor listings (per zip, single page)
4. Normalize both into common format
5. Deduplicate Layer 1: group by normalized address, merge
6. Geocode any listings missing lat/lng
7. Upsert into DB (insert new, update existing)
   - Track price changes in price_history_json
   - Reset details_fetched if enrichment failed
8. Score all listings (18 factors, weighted composite)
9. Deduplicate Layer 2: DB cleanup for post-upsert dupes
10. Street Watch: match events against active watches
11. Update registry: pipeline_last_run, listing_count
```

### Address Deduplication

`_normalize_address()`: lowercase, strip punctuation, expand abbreviations (St→Street, Dr→Drive, Ave→Avenue), remove city/state/zip suffixes.

`_merge_listing_data()`: when two sources list the same property, prefer Zillow source_id, backfill missing fields from Realtor.

### Scraper: Zillow

- API: "Real-Time Real-Estate Data" on RapidAPI ($25/mo PRO)
- Pagination: 41 results/page, up to 5 pages per zip
- Rate limiting: 1s between pages, 1s between zips
- 5xx errors raise `TransientAPIError` (retried on next run)
- Detail enrichment: separate `fetch_zillow_detail(zpid)` call, lazy on first view

### Scraper: Realtor

- API: "Realty In US" on RapidAPI ($20/mo PRO)
- Single POST per zip, 50 results limit
- Returns richer structured data (details sections, tags)
- Detail enrichment: `fetch_realtor_detail(property_id)`

### Upsert Logic

- Match by `source_id` (e.g., `"zillow_12345"`)
- Update path: track price changes, update mutable fields, reset failed enrichment
- Insert path: create new Listing, compute initial days_on_market

---

## 8. The 18-Factor Scoring Engine

All scores are 0-100. Higher = better for the buyer. The composite is a weighted average using user-customizable importance weights (0-10 scale).

### Factor Details

| # | Factor | What It Measures | Key Thresholds |
|---|--------|-----------------|----------------|
| 1 | **Price** | How far under budget | Sweet spot: min to 70% of max → 70-100 |
| 2 | **Size** | Living area sqft | 2000→70, 3000+→100 |
| 3 | **Yard** | Lot size | ≥10K sqft→75-100 |
| 4 | **Features** | Garage+Porch+Patio+Beds+Baths | 20pts each, cap 100 |
| 5 | **Flood** | Flood risk | Above plain→100, FEMA X/C→85, Below→20 |
| 6 | **Year Built** | Age/maintenance | 2020+→100, 1960→~30 |
| 7 | **Single Story** | Accessibility | Yes→100, 2 stories→40 |
| 8 | **Price/SqFt** | Value density | ≤$120→100, >$275→5-30 |
| 9 | **Days on Market** | Seller motivation | 90+→100, <7→10 |
| 10 | **HOA** | Monthly cost | $0→100, >$500→5 |
| 11 | **Proximity Medical** | Hospital distance | <2mi→100, 15+→5 |
| 12 | **Proximity Grocery** | Grocery distance | <1mi→100, 10+→5 |
| 13 | **Community Pool** | Amenity | Yes→100, No→20 |
| 14 | **Property Tax** | Tax rate vs value | ≤0.3%→100, >1%→5-30 |
| 15 | **Lot Ratio** | Lot-to-house ratio | 6:1+→100, <1.5:1→10-30 |
| 16 | **Price Trend** | Price direction | ≤-10%→100, +10%+→5-20 |
| 17 | **Walkability** | External metric | Passthrough 0-100 |
| 18 | **Proximity POI** | User landmark distance | Haversine: <1mi→100, 15+→0 |

### Default Importance Weights

```python
price: 8, size: 5, yard: 7, features: 8, flood: 6,
year_built: 5, single_story: 7, price_per_sqft: 4,
days_on_market: 3, hoa: 6, proximity_medical: 5,
proximity_grocery: 5, community_pool: 6, property_tax: 4,
lot_ratio: 3, price_trend: 4, walkability: 3,
proximity_poi: 0  # disabled by default
```

### Composite Calculation

1. Compute all 18 sub-scores
2. Read user's importance weights (or defaults)
3. Normalize weights to sum to 1.0
4. Weighted average: `composite = Σ(score[i] × weight[i] / total_weight)`

### Per-User Personalization

`DealScore.compute_user_composite(user_prefs)` recalculates the composite using the current user's importance weights AND their price range. This means the same listing shows a different score for different users. Called on every dashboard load.

---

## 9. Dashboard & Listing Browsing

### Route: `GET /`

The main listing grid. Features:

**Filtering:**
- By flag: All / Favorites / Maybes / Hidden / Unflagged
- By source: All / Zillow / Realtor / Agent / Friend
- By deal score range: Min Score slider
- By target area (named zip groups configured by owner)

**Sorting:**
- Deal Score (default, descending)
- Price (asc/desc)
- Newest (by first_seen)
- Nearest to Me (uses browser Geolocation API)

**Listing Cards show:**
- Primary photo
- Address, city, zip
- Price
- Beds / Baths / SqFt / Lot SqFt
- Deal score badge (color-coded: green ≥75, yellow 50-74, red <50)
- Flag indicator (heart=favorite, ?=maybe, eye-slash=hidden)
- Source badge

**Clickable Cards:** The entire listing card is clickable — navigating to the listing detail page. Interactive child elements (links, buttons, forms, dropdowns) still work independently via an `event.target.closest()` guard that skips card navigation when the click hits an interactive element. Hover effect: slight upward lift (`translateY(-1px)`) with background darkening to `#f3f4f6`. At help level 2+, a tooltip reads "Click anywhere on this card to see full details."

**"Since your last visit" banner:** Shows count of new listings since last login.

**Portfolio Analysis panel:** Expandable section at top. User selects a flag category (favorites/maybes/hidden), clicks "Ask Claude," gets ranked comparison with strategy advice.

### Route: `GET /digest`

Tabular view of all listings with CSV export. Shows address, price, beds, baths, sqft, deal score, area, source, first seen, flags. Filterable.

---

## 10. Listing Detail & Enrichment

### Route: `GET /listing/<id>`

**Immediate render (no blocking API calls):**
- Photo carousel (multiple photos, swipeable)
- Property stats: price, beds, baths, sqft, lot, year built, stories, HOA, tax
- Deal score breakdown: horizontal bar chart of all 18 factors with per-factor scores
- Price history timeline (if multiple price events)
- Map with property pin + nearby landmarks
- User flag controls (favorite/maybe/hide)
- Listing notes (free-form + status checkboxes)
- Share & Collect controls

**Lazy enrichment:**
If `details_fetched == False`, shows a "Fetch Property Details" button. Clicking it fires AJAX `POST /listing/<id>/enrich`:
- Calls Zillow or Realtor detail API
- Returns enriched data: full description, detailed features (Interior, Heating/Cooling, etc.), accurate has_garage/porch/patio
- Updates the DOM in place without page reload
- On transient API error (5xx), does NOT mark `details_fetched=True` → user can retry

**AI Deal Brief:**
"Ask Claude" button fires AJAX `POST /listing/<id>/analyze`:
- Sends listing data + deal scores + user preferences to Claude
- Returns JSON: summary, strengths (bullet points), concerns (bullet points), negotiation leverage with specific dollar offer, verdict (strong_buy / worth_considering / pass)
- Cached per user per listing in `CachedAnalysis`

---

## 11. Preferences & Scoring Customization

### Route: `GET/POST /preferences`

Multi-section preference page:

**Section 1: Search Criteria**
- Min/max price (dual-handle range slider with visual bar)
- Min beds, min baths
- Must-haves: garage, porch, patio (checkboxes)

**Section 2: Scoring Importance Weights**
- 18 sliders (0-10) for each scoring factor
- Color-coded: 0=off (gray), 1-3=low (blue), 4-6=mid (yellow), 7-10=high (red)
- Near Landmark dropdown: select from site landmarks or user landmarks
- "Great Deal" threshold slider (composite score cutoff)
- **Power Mode controls slider visibility** (see below) — hidden sliders preserve their values via hidden `<input>` elements so weights are never lost
- An "Unlock" link appears at the bottom of the visible sliders, pointing users to the next power level

**Section 3: User Landmarks (My Landmarks)**
- Up to 3 personal POI per user
- Typeahead search via Nominatim (free geocoding)
- Mini Leaflet map picker (click to place pin)
- Saved landmarks appear in the Near Landmark dropdown under "My Landmarks" optgroup
- AJAX CRUD: `POST /my-landmarks`

**Section 4: Target Areas** *(owner and master roles only)*
- Interactive map showing zip code polygons (GeoJSON from OpenDataDE)
- Click polygons to assign/unassign zips to named areas
- Owner configures the master area map; users see labeled areas
- Master users can add new zips (`canAddZips` flag)
- **Hidden for non-owner/master users** — the entire Target Areas map section is not rendered for agent, client, principal, or guest roles
- The Target Areas summary card was removed from the scoring section (redundant with the map)

**Section 5: Avoid Areas**
- Census-defined place names that hide listings from dashboard
- Autocomplete search: `POST /api/places`

**Section 6: AI Preferences Coach**
- "Analyze My Setup" button fires AJAX `POST /analyze-preferences`
- Returns: headline, strengths, blind_spots, tweaks (specific slider changes), local_insight, bottom_line

**AJAX save:** Entire preferences form saves via AJAX (`POST /preferences` with `X-Requested-With: XMLHttpRequest`). No page reload. Status message shown inline.

**Guest support:** Preferences stored in `session["guest_prefs"]`. Survives browser session.

### 11.1 Help Level System (1/2/3)

Stored in `preferences_json` as `help_level`. Default: 2 (Standard) for registered users, 3 (Guided) for guests.

| Level | Name | Behavior |
|-------|------|----------|
| 1 | Expert | No tooltips, no inline hints — clean UI for power users |
| 2 | Standard | Bootstrap tooltips on elements with `data-help` attributes |
| 3 | Guided | Tooltips + visible `.help-hint` inline explanation blocks |

**Toggle location:** Help dropdown in the navbar (instant AJAX save, no reload). Also shown at the top of the Preferences page.

**Route:** `POST /api/help-level` — AJAX endpoint, saves to `preferences_json` (or `session["guest_prefs"]` for guests).

**Context processor:** `help_level` is injected into all templates so any page can conditionally render hints.

**JS module:** `app/static/js/help-hints.js` — initializes Bootstrap tooltips on `[data-help]` elements, toggles `.help-hint` visibility based on current level.

**Tooltip coverage** (at level 2+):
- All left nav icons: Dashboard, Map, Digest, Favorites, Watch, Tour, Preferences, Feedback
- All dashboard filter labels: Area, Sort, Flag, Source, Min Score
- Deal score ring on listing cards
- Deal Score card on listing detail page (with level 3 inline hint)
- AI "Analyze This Deal" button
- "Fetch Property Details" button
- Price Range header (with level 3 inline hint)
- Great Deal Threshold label
- Near Landmark label

### 11.2 Power Mode (Low / Mid / High)

Stored in `preferences_json` as `power_mode`. Default: `"high"` for registered users, `"low"` for guests.

Controls two UI dimensions: **nav icon visibility** and **scoring slider visibility**.

| Mode | Nav Icons | Scoring Sliders |
|------|-----------|----------------|
| **Low** | Core: Dashboard, Map, Favorites, Preferences, Help | 6 basic: Price, Size, Yard, Features, Flood, Year Built |
| **Mid** | + Digest, Watch, Social, Feedback | + 6 intermediate: Single Story, Price/SqFt, Days on Market, HOA, Property Tax, Price Trend |
| **High** | Everything (all nav icons) | + 6 location: Near Landmark, Near Medical, Near Grocery, Community Pool, Lot Ratio, Walkability |

**Hidden sliders preserve values:** When a slider is hidden by a lower power mode, its current weight value is preserved in a hidden `<input>` so the user's scoring configuration is never lost when switching modes.

**"Unlock" prompt:** At the bottom of the visible slider group, an "Unlock" link is shown pointing to the next power level (e.g., "Unlock 6 more sliders — switch to Mid mode").

**Toggle location:** Help dropdown in the navbar and Preferences page — instant AJAX save, no reload.

**Route:** `POST /api/power-mode` — AJAX endpoint, saves to `preferences_json` (or `session["guest_prefs"]` for guests).

---

## 12. AI Deal Analyst (Claude Integration)

### Service: `app/services/deal_analyst.py`

**Model:** `claude-sonnet-4-20250514`
**Endpoint:** `https://api.anthropic.com/v1/messages`

### Three Analysis Types

**1. Deal Brief** (`analyze_listing`)
- Input: listing data + deal score breakdown + buyer preferences
- Output: `{summary, strengths, concerns, negotiation, verdict}`
- Verdict: `strong_buy` / `worth_considering` / `pass`
- The negotiation field includes a specific dollar amount for opening offer
- max_tokens: 1024, timeout: 30s

**2. Portfolio Analysis** (`analyze_portfolio`)
- Input: set of flagged listings with composites + buyer preferences
- Output: `{headline, ranking, patterns, strategy, dark_horse, bottom_line}`
- Ranks properties best to worst with reasoning
- Identifies the "dark horse" — underrated pick the buyer may have missed
- max_tokens: 2048, timeout: 60s

**3. Preferences Coach** (`analyze_preferences`)
- Input: current weights vs default weights + buyer criteria
- Output: `{headline, strengths, blind_spots, tweaks, local_insight, bottom_line}`
- Specific slider change recommendations with rationale
- max_tokens: 1536, timeout: 45s

### Prompt Architecture

**Context builders** (`app/services/ai_context.py`) are pure functions (no I/O):
- `build_listing_context()` — comprehensive property + score + preferences text
- `build_compact_listing()` — one-block summary for portfolio entries
- `build_portfolio_context()` — system context (buyer profile + `{{BASE_PROMPT}}` placeholder) + user message (listing blocks)
- `build_preferences_context()` — current vs default weights comparison

**Default prompts** are in `config.DEFAULT_PROMPTS`. Owners and agents can override them per-type via the Prompts admin page (stored in `PromptOverride` model).

**Prompt resolution order:** Agent-specific → Site-wide → Default.

### Error Handling

- `_call_anthropic()` wraps all API calls
- Strips markdown fences from JSON responses
- Returns `{error: "...", _meta: {response_time_ms, http_status, tokens}}` on failure
- Every call logged to `ApiCallLog` for billing/diagnostics

### Caching

Results cached in `CachedAnalysis` table. Unique key: `(user_id, analysis_type, listing_id)`. No TTL — user can re-analyze to get fresh results.

---

## 13. Map View

### Route: `GET /map`

Full-screen Leaflet map showing all active listings as markers:
- Color-coded by deal score (green/yellow/red)
- Click marker → popup with address, price, score, link to detail
- Site landmarks shown as distinct markers
- User landmarks shown if configured
- Map center and bounds from site registry config
- OpenStreetMap tiles (free, no API key)

---

## 14. Tour Planner

### Route: `GET /itinerary`

Shows the user's flagged listings organized for touring:
- Favorites and Maybes grouped separately
- Each listing shows: address, price, deal score, user notes, visit status
- Visit status badges: Visited (blue), Scheduled (yellow), Made Offer (green), Not Interested (gray)
- Contact Agent button (for clients with assigned agents)

---

## 15. Street Watch

### Routes

| Route | Method | Purpose |
|-------|--------|---------|
| `POST /watch/quick` | AJAX | Create a street watch |
| `GET /watch/streets` | AJAX | Autocomplete street names |
| `POST /watch/remove/<id>` | AJAX | Deactivate a watch |
| `GET /watch` | Page | Watch management |
| `GET /watch/unsubscribe/<token>` | Link | Email unsubscribe |

### How It Works

1. User enters a street name and zip code (or clicks "Watch this street" on a listing)
2. Street name is normalized (expand abbreviations, uppercase)
3. System creates a StreetWatch record with unique unsubscribe token
4. After each pipeline run, system matches new/changed listings against watches:
   - `new_listing` — new property on watched street
   - `price_drop` — price decreased on watched property
   - `back_on_market` — previously inactive listing re-appeared
5. StreetWatchAlert records created (idempotent)
6. Email digests sent to watchers with alert details

### Guest Support

Guests provide an email for watches. At registration, watches are linked to the new account via `link_watches_to_user()`.

---

## 16. Agent Features

### Routes

| Route | Purpose |
|-------|---------|
| `GET /agent/dashboard` | Client roster, pending friend listings, branding |
| `POST /agent/clients/create` | Create client account + welcome email |
| `POST /agent/clients/resend-welcome` | Resend temp password (AJAX) |
| `GET/POST /agent/clients/<id>/prefs` | View/edit client preferences |
| `POST /agent/clients/<id>/notes` | Private notes on client (AJAX) |
| `GET/POST /agent/prompts` | Agent-specific AI prompt overrides |
| `POST /agent/branding` | Color, logo, icon, tagline, tagline style |
| `GET/POST /agent/friend-listing/<id>/review` | Review submitted home |
| `POST /agent/friend-listing/<id>/approve` | Approve → creates real Listing |
| `POST /agent/friend-listing/<id>/reject` | Reject with reason |
| `GET/POST /agent/add-listing` | Agent creates listing directly (source="agent") |

### Agent Branding

Agents customize their appearance in the navbar:
- `brand_color` — hex color for navbar accent
- `brand_icon` — Bootstrap Icon key (e.g., "bi-house-heart-fill")
- `brand_logo_url` — URL to custom logo image
- `brand_tagline` — short text shown in navbar
- `brand_tagline_style` — display variant (plain, italic, bold, etc.)

When an agent's client logs in, they see the agent's branding.

### Friend Listing Workflow

1. User submits a home via `/social/add-home` (address, price, beds, baths, sqft, description, photos, relationship, permission)
2. Listing appears on agent dashboard with "Pending Review" status
3. Agent reviews: sees details, can edit, then approve or reject
4. **Approve** → creates a real Listing (source="friend") in the main feed + awards points to submitter
5. **Reject** → records reason, notifies submitter

---

## 17. Owner Administration

### Routes

| Route | Purpose |
|-------|---------|
| `GET /admin/metrics` | API usage breakdown: AI calls, fetches, cost, per-user |
| `POST /admin/metrics/refresh` | AJAX refresh of metrics data |
| `POST /fetch-now` | Trigger pipeline manually (returns streaming log) |
| `POST /toggle-scheduler` | Pause/resume nightly pipeline |
| `GET /admin/diagnostics` | Per-call API diagnostics (response times, status codes) |
| `GET /admin/prompts` | View/edit site-wide AI prompts |
| `POST /admin/prompts/validate` | AJAX: validate prompt syntax |
| `POST /admin/prompts/preview` | AJAX: test prompt with sample listing |
| `GET /admin/agents` | Agent applications dashboard |
| `POST /admin/agents/<id>/action` | Approve/suspend/reactivate agents |
| `POST /admin/agents/<id>/notes` | Owner notes on agents (AJAX) |
| `GET /admin/users` | User account management |
| `POST /admin/users/<id>/action` | Suspend/reactivate/delete/edit users |
| `GET /admin/billing` | Billing plan configuration |
| `POST /admin/billing` | Update billing settings |
| `POST /admin/landmarks` | Add/remove site POI landmarks (AJAX) |
| `POST /feedback` | Submit feedback (all users, AJAX) |
| `GET /admin/feedback` | Feedback review page (owner+) |
| `POST /admin/feedback/<id>/read` | Mark feedback as read (AJAX) |

### Metrics Page

Shows:
- Total AI calls (all time + 30 day)
- Total fetches (all time + 30 day)
- Estimated cost (all time + 30 day)
- Per-user breakdown table
- Cost estimates per call type (color-coded badges)
- Recent activity log (last 50 calls)
- Pipeline log output (when manually triggered)

### User Management

Table of all accounts showing: username, email, role (badge), status (active/suspended), created, last login. Actions: masquerade (eye icon), delete (trash icon). Owner accounts cannot be deleted from this page.

### Feedback System

**Submission (all users):** A floating feedback icon in the left nav bar (positioned between Preferences and Help) opens a modal overlay. The modal contains:
- 3 sentiment buttons: thumbs up (positive), meh (neutral), thumbs down (negative)
- Optional comment textarea
- Optional email field (shown for guests only, so they can be contacted)
- AJAX submission via `POST /feedback` — no page reload, inline success confirmation

**Admin review (`GET /admin/feedback`):** Owner/master feedback review page showing all submissions in reverse chronological order. Each entry shows sentiment icon, comment, submitter info, timestamp, and page URL. Owners can mark individual entries as read via `POST /admin/feedback/<id>/read` (AJAX toggle). An unread badge count appears on the "Feedback" link in the right-side admin nav.

**Model:** `Feedback` in `models_social.py`. Migration creates the `feedback` table.

---

## 18. Master Site Management

### Routes

| Route | Purpose |
|-------|---------|
| `GET /admin/sites` | List all sites with live listing counts |
| `POST /admin/sites/create` | Create new site + initialize DB |
| `POST /admin/sites/<key>/edit` | Update site config |
| `POST /admin/sites/<key>/toggle` | Activate/deactivate |
| `POST /admin/sites/<key>/delete` | Remove site (renames DB) |
| `GET /admin/sites/<key>/nginx` | Get nginx config snippet (JSON) |
| `GET /admin/sites/api/list` | JSON list of all sites |

### Site Creation

1. **Location Picker modal** — search by city/state via Nominatim
2. Auto-populates: site_key, display_name, map center, bounds, first zip
3. **Map Picker modal** — click to set center, shift+drag for bounds
4. **ZIP Picker modal** — loads state GeoJSON, click polygons to select zips
5. On create: initializes per-site DB, seeds 4 operator accounts (master/owner/agent/user using master's email), applies migrations

### Site Cards

Each site shown as a card with:
- Display name, site key, DB path
- Pipeline last run timestamp
- Listing count
- Zip codes (chips)
- Edit configuration link
- Activate/deactivate toggle
- Delete button

---

## 19. Social Features

### 19.1 Sharing

**Share a listing** (`POST /social/share`):
- Recipient email, name, relationship, personal message
- Generates unique share_token for public URL
- Sends email notification
- Awards points to sharer

**Share landing** (`GET /social/s/<token>`):
- Hero display: listing photo, address, price, deal score
- Reactions bar (5 reaction types with icons)
- CTA to register / browse more listings
- Tracks view/click events

**Copy link** (`POST /social/copy-link/<listing_id>`):
- Returns JSON with shareable URL
- No email sent — for social media, messaging apps

### 19.2 Reactions

5 types: Love It (heart), Interested (eye), Great Location (pin), Too Pricey ($), Not For Me (X).

Each reaction has an icon, label, and color. One reaction per email per share. Awards points to the original sharer.

### 19.3 Collections

- Create named collections with descriptions
- Add/remove listings (with optional notes and ordering)
- Share entire collections via email (separate share flow)
- Public collection view for recipients

### 19.4 Referrals

- Generate unique referral code per user
- Send invitation emails
- Referral landing page sets session attribution
- Loop closes at registration → referrer gets points
- Status progression: invited → registered → active → converted

### 19.5 Points & Leaderboard

**7 earning actions:**
| Action | Points |
|--------|--------|
| Share a listing | 1 |
| Receive a reaction | 3 |
| Create a collection | 2 |
| Referral registers | 10 |
| Submit friend listing | 5 |
| Create a listing (agent) | 5 |
| Listing approved | 3 |

**Daily cap:** 50 points max per user per day.

**Leaderboard:** Monthly rankings by total points. Shows top sharers, most reactions received.

### 19.6 Social Analytics (Admin)

Owner/master view of site-wide social metrics: total shares, reactions, collections, referrals, engagement rates.

---

## 20. Billing & Quota System

### Plan Tiers

| Plan | AI/month | Fetch/month | Budget |
|------|---------|------------|--------|
| Free | 10 | 50 | $1 |
| Basic | 100 | 500 | $10 |
| Pro | 500 | 2,000 | $50 |
| Unlimited | ∞ | ∞ | ∞ |

### Quota Enforcement

`check_quota(site_key, call_type)` → `(allowed, reason)`:
- Classifies call_type as AI or Fetch
- Counts calls in current billing cycle
- Returns False + reason if limit exceeded
- Routes return HTTP 429 when quota blocked

### Budget Alerts

Email alerts sent at 80% and 100% of monthly_budget threshold.

### Call Type Classification

- **AI:** anthropic_deal, anthropic_portfolio, anthropic_prefs
- **Fetch:** zillow, realtor, zillow_detail, realtor_detail, google_places, google_geocode

---

## 21. Email System

### Templates (5)

1. `email/share_notification.html` — "X shared a listing with you"
2. `email/reaction_notification.html` — "X reacted to your share"
3. `email/collection_share_notification.html` — "X shared a collection"
4. `email/referral_invitation.html` — "Join HomeFinder"
5. `email/social_digest.html` — Weekly activity summary

### Additional Email Contexts (auth templates)

- `auth/verify_email_body.html` — Verification link
- `auth/reset_email_body.html` — Password reset link
- `auth/welcome_email_body.html` — Welcome after registration
- `auth/client_welcome_email_body.html` — Agent-created client welcome

### Configuration

Flask-Mail over SMTP (Gmail default). Environment variables: `MAIL_SERVER`, `MAIL_PORT`, `MAIL_USE_TLS`, `MAIL_USERNAME`, `MAIL_PASSWORD`, `MAIL_DEFAULT_SENDER`.

---

## 22. Documentation System

### Routes

| Route | Purpose |
|-------|---------|
| `GET /docs` | Documentation index (role-filtered) |
| `GET /docs/content/<path>` | Raw file content (JSON) |
| `POST /docs/upload` | Upload doc (owner+) |
| `POST /docs/delete/<path>` | Delete doc (owner+) |

Role-based access: agents see agent docs, owners see owner+agent docs, masters see all.

---

## 23. Frontend Architecture

### Template Hierarchy

```
base.html (navbar, modals, scripts, flash messages)
├── All page templates extend base.html
├── Partial includes prefixed with _ (e.g., _prefs_scoring.html)
└── Email templates are standalone (no base.html inheritance)
```

### base.html Key Components

- **Responsive navbar** with role-aware menu items
- **Left nav icons** with power-mode-gated visibility (Low/Mid/High) and `data-help` tooltips at help level 2+
- **Feedback modal** — floating icon in left nav (between Preferences and Help); opens sentiment + comment form; AJAX submission
- **Help Level toggle** in Help dropdown — 1/2/3 selector with instant AJAX save
- **Power Mode toggle** in Help dropdown — Low/Mid/High selector with instant AJAX save
- **Agent branding** (custom color/icon/logo/tagline)
- **Two guest modals:** `welcomeModal` (first visit, cookie-gated) and `joinModal` (feature gate with custom messages)
- **Contact Agent modal** (for clients/principals)
- **Flash messages** (dismissible Bootstrap alerts)
- **Masquerade banner** (yellow alert when impersonating)
- **Service worker registration** (PWA)
- **Twemoji parsing** for consistent emoji rendering

### CSS

Single file: `app/static/css/style.css`. Bootstrap 5 base with custom overrides.

### JavaScript Files

| File | Purpose |
|------|---------|
| `preferences.js` | Dual-handle price slider, importance sliders (color-coded 0-10), AJAX form save, AI preferences analysis |
| `landmarks.js` | User landmark CRUD (max 3), admin landmark management, Nominatim search, Leaflet map picker |
| `help-hints.js` | Help level system: initializes Bootstrap tooltips on `[data-help]` elements, toggles `.help-hint` block visibility based on `help_level` (1=off, 2=tooltips, 3=tooltips+hints) |
| `site-manager.js` | Map Picker (click center, shift+drag bounds), Location Picker (typeahead → auto-fill), ZIP Picker (state GeoJSON, click polygons) |
| `sw.js` | Service worker: cache-first for static, network-first for HTML |

### AJAX Patterns

All AJAX follows a consistent pattern:
```javascript
fetch(url, {
    method: 'POST',
    body: new FormData(form),
    credentials: 'same-origin',
    headers: { 'X-Requested-With': 'XMLHttpRequest' },
})
.then(r => r.json())
.then(data => {
    if (data.ok) { /* update DOM */ } else { /* show error */ }
})
```

Standard response shape: `{ok: bool, message?: string, error?: string, ...data}`

### DOM Manipulation Priority

**Critical rebuild requirement:** Actions that add/remove items from the page (flagging, deleting watches, removing collection items, etc.) must use DOM manipulation — never a full page reload. Current implementation already follows this for most AJAX endpoints. Areas to ensure:

- Flag toggling (no reload)
- Note saving (no reload)
- Enrichment loading (no reload)
- AI analysis display (no reload)
- Landmark add/remove (DOM rebuild)
- Collection item add/remove (DOM update)
- Street watch add/remove (DOM update)
- Share/react (inline update)
- Feedback submission (modal closes, success toast)
- Help level toggle (tooltips/hints show/hide instantly)
- Power mode toggle (nav icons + sliders show/hide instantly)

---

## 24. Static Assets & PWA

### Files

```
app/static/
├── css/style.css              # Single stylesheet
├── js/preferences.js          # Scoring sliders + AJAX save
├── js/landmarks.js            # User/admin landmark management
├── js/help-hints.js           # Help level tooltips + inline hints
├── js/site-manager.js         # Map/Location/ZIP picker modals
├── sw.js                      # Service worker
├── manifest.json              # PWA manifest
├── icons/icon-192.png         # App icon small
├── icons/icon-512.png         # App icon large
└── uploads/.gitkeep           # Friend listing photo uploads
```

### PWA Support

- `manifest.json` defines app name, icons, theme color (#1a1a2e)
- Service worker caches static assets (cache-first) and HTML pages (network-first with fallback)
- Install banner on mobile: detects device, shows after 2s delay, captures `beforeinstallprompt`
- iOS: instructions to tap Share → "Add to Home Screen"
- Cookie `hf_install_dismissed=1` prevents re-showing

---

## 25. Configuration & Environment

### `config.py` Constants

```python
MAX_PRICE = 600_000
MIN_BEDS = 4
MIN_BATHS = 3
MUST_HAVE = ["garage", "porch", "patio"]
AVOID_AREAS = ["East Goose Creek", "Upper Summerville"]
GREAT_DEAL_SCORE_THRESHOLD = 75
DEFAULT_IMPORTANCE = { ... }  # 18 scoring weights
DEFAULT_PROMPTS = { ... }     # 3 AI prompt types
```

### Environment Variables (`.env`)

```
SECRET_KEY=...
RAPIDAPI_KEY=...
ANTHROPIC_API_KEY=...
GOOGLE_MAPS_KEY=...          # optional geocoding fallback
GEOAPIFY_KEY=...             # optional geocoding fallback
FETCH_INTERVAL_HOURS=6
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=...
MAIL_PASSWORD=...
MAIL_DEFAULT_SENDER=HomeFinder <noreply@homefinder.local>
```

---

## 26. Error Handling & Logging

### API Error Patterns

- **TransientAPIError** — raised on 5xx from Zillow/Realtor. Caller catches it, skips `details_fetched=True`, retries on next access.
- **Quota exceeded** — returns HTTP 429 with JSON `{error: "quota exceeded", reason: "..."}`
- **Claude API errors** — caught in `_call_anthropic()`, returned as `{error: "..."}`

### Logging

```python
log = logging.getLogger(__name__)
```

- Startup markers: `log.warning("Module vX loaded")`
- Pipeline progress: `log.info("Zillow: N results for ZIP")`
- API failures: `log.error("API error STATUS: BODY")`
- All external calls logged to `ApiCallLog` with response_time_ms, http_status, quota_remaining

### Improvement: Structured Logging

**Recommendation for rebuild:** Adopt structured JSON logging (e.g., `python-json-logger`) to make log parsing and monitoring easier. Include request_id, site_key, user_id in every log line.

---

## 27. Testing

### Current Test Suite

84 integration tests across 7 files:

| File | Scope |
|------|-------|
| `test_auth.py` | Registration, login, verification, password reset |
| `test_models.py` | ORM model creation, relationships, methods |
| `test_scoring.py` | 18-factor scoring, composite calculation |
| `test_engagement.py` | Flags, notes, AI analysis, enrichment |
| `test_social_phase2.py` | Social sharing, reactions, collections, referrals, points |
| `test_street_watch.py` | Watch CRUD, alerts, email digests |
| `conftest.py` | Shared fixtures (app, client, test user, test site) |

Run: `pytest` from project root.

---

## 28. Deployment

### IIS (Current Production)

- `web.config` configures HttpPlatformHandler → Waitress
- App pool: `HomeFinderAgents` (No Managed Code, Integrated pipeline, LocalSystem identity)
- After code changes: clear `__pycache__`, recycle app pool
- Pipeline: Windows Task Scheduler (not in-process)
- URL prefix: `/home_finder_agents_social`

### Linux (Secondary)

- Gunicorn behind Nginx
- `wsgi.py` with `PrefixMiddleware` (strips URL prefix, sets SCRIPT_NAME)
- `gunicorn.ctl` socket file

### Local Development

```bash
python run_waitress.py  # Serves on http://localhost:8080/home_finder_agents_social/
```

---

## 29. Improvement Recommendations

These are observations from reviewing the entire codebase — areas where a rebuild could do better.

### 29.1 Backend Structure & Debugging

1. **Structured logging** — Replace `logging.getLogger(__name__)` with a project-wide structured logger that includes `request_id`, `site_key`, `user_id`, and `duration_ms` in every log line. Use JSON format for machine-parseable logs. Add a `/admin/logs` viewer for owners.

2. **Request tracing** — Generate a unique request ID in middleware, propagate through all service calls and API requests. Include in error responses so users can report "Request ID: abc123" for debugging.

3. **Health check endpoint** — Add `GET /health` that verifies: registry.db accessible, at least one site DB readable, SMTP reachable (optional), RapidAPI key valid (cached check). Return JSON with component status.

4. **Service layer contracts** — Formalize service function signatures with dataclasses or TypedDict for inputs/outputs instead of raw dicts. Makes IDE support better and catches type errors early.

5. **Migration versioning** — Replace the check-before-alter pattern with a proper migration version table. Store `schema_version` per site and apply numbered migration functions in order. Eliminates redundant PRAGMA table_info checks on every request.

### 29.2 Frontend & UX

6. **Client-side filtering** — Currently, changing sort order or flag filter triggers a full form POST. Move filtering and sorting to JavaScript (the data is already on the page in the listing cards). Only fetch from server when the actual data set changes (e.g., different site or new pipeline run).

7. **Infinite scroll or virtual list** — Replace pagination (if any) with infinite scroll for the dashboard grid. Load 20 listings initially, fetch more as user scrolls. Reduces initial page weight for sites with hundreds of listings.

8. **Optimistic UI updates** — When a user flags a listing, update the card immediately (optimistic) and revert on failure. Current AJAX already does this but be consistent everywhere.

9. **Toast notifications** — Replace `flash()` messages (which require a page load to appear) with a toast notification system for AJAX actions. Bootstrap 5 has built-in toast support.

10. **Skeleton loading states** — Show card skeletons while dashboard loads instead of a blank page or spinner. Better perceived performance.

### 29.3 Data Pipeline

11. **Pipeline progress streaming** — The "Fetch Now" button currently returns results after the full pipeline completes. Stream progress via Server-Sent Events (SSE) so the owner sees real-time status: "Fetching zip 29401... 23 results... Scoring... Done."

12. **Retry with backoff** — Currently, transient API errors are just skipped until next run. Add exponential backoff retry (1s, 2s, 4s) within the same pipeline run for 5xx errors.

13. **Parallel zip fetching** — Currently zips are fetched sequentially. Use `concurrent.futures.ThreadPoolExecutor` to fetch multiple zips in parallel (respecting rate limits).

### 29.4 Reliability

14. **Database backups** — Add a scheduled backup that copies all `.db` files to a timestamped backup directory. SQLite's `.backup()` API does this safely even while the app is running.

15. **Circuit breaker for external APIs** — If Zillow/Realtor returns 5xx three times in a row, stop calling for 15 minutes. Prevents wasting quota on a down API.

16. **Graceful degradation** — If the Anthropic API is unreachable, show a clear "AI analysis temporarily unavailable" message instead of a generic error. Same for scraper APIs.

17. **Rate limit headers** — Surface RapidAPI `X-RateLimit-Remaining` to the owner metrics page so they can see quota status without checking RapidAPI dashboard.

### 29.5 Security

18. **CSRF tokens** — Ensure all POST forms include CSRF protection (Flask-WTF or manual token). Current implementation should be audited.

19. **Rate limiting on public endpoints** — Share landing pages, referral landing pages, and the registration endpoint should have rate limits to prevent abuse.

20. **Input sanitization** — Friend listing descriptions and share messages should be sanitized for XSS before rendering in templates.

### 29.6 Architecture

21. **API-first design** — Consider building all routes as JSON API endpoints first, then having templates call them. This makes mobile app support, third-party integrations, and testing much easier. The current hybrid (some routes return HTML, some return JSON based on `X-Requested-With`) works but is inconsistent.

22. **Background task queue** — Replace direct-call patterns for email sending and AI analysis with a lightweight task queue (e.g., `huey` with SQLite backend). Prevents request timeouts on slow Claude responses and allows retry logic.

23. **Event sourcing for social** — Social actions (share, react, collect, refer) are natural events. Consider an event log that drives projections (point balances, leaderboard, analytics) rather than computing them from multiple tables.

---

*This document is the complete specification for rebuilding HomeFinder Social. Every route, model, service, template, and behavior described here has been verified against the current codebase as of 2026-03-17.*
