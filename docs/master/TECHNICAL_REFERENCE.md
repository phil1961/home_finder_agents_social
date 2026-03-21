# HomeFinder — Technical Reference

**Version:** 2026.03.20a
**Last Updated:** 2026-03-20

---

## Architecture Overview

HomeFinder is a **multi-tenant Flask web application** for real estate listing discovery with AI-powered deal scoring. Each market (site) operates on its own SQLite database; a central registry database tracks all site instances.

```
┌──────────────────────────────────────────────────────────┐
│  IIS (HttpPlatformHandler)                               │
│    └─ Waitress WSGI Server (4 threads)                   │
│        └─ Flask App (factory pattern)                    │
│            ├─ SitePathMiddleware    ← tenant routing     │
│            ├─ MultiTenantSQLAlchemy ← per-site engines   │
│            ├─ Blueprints (5)                             │
│            │   ├─ dashboard (/)                          │
│            │   ├─ auth (/auth)                           │
│            │   ├─ social (/social)                       │
│            │   ├─ site_manager (/admin/sites)            │
│            │   └─ docs (/docs)                           │
│            └─ Services                                   │
│                ├─ deal_analyst  (Claude AI)               │
│                ├─ registry     (site catalog)             │
│                ├─ street_watch (street monitoring)        │
│                ├─ place_geocoder (Census TIGER)           │
│                ├─ points       (gamification)             │
│                ├─ billing      (quota & budget)           │
│                └─ social_digest (weekly digests)          │
└──────────────────────────────────────────────────────────┘
          │                              │
    ┌─────┴─────┐                ┌───────┴────────┐
    │ Registry   │                │ Per-Site DBs   │
    │ registry.db│                │ charlestonsc.db│
    │ (sqlite3)  │                │ catonsvillemd.db│
    └────────────┘                └────────────────┘
```

## Multi-Tenant Routing

### SitePathMiddleware (WSGI)

Intercepts every request and extracts the site key from the URL path:

```
/home_finder_agents/site/charleston/preferences
  → HTTP_X_HOMEFINDER_SITE = "charleston"
  → /home_finder_agents/preferences  (stripped for Flask)
```

### Per-Request Site Binding

On each request, `before_request` calls `select_site()`:

1. Looks up site in `registry.db` by key
2. Creates/caches a SQLAlchemy engine for that site's SQLite file
3. Sets `g.site` (config dict) and `g.site_engine` (engine)
4. All ORM queries transparently route to the correct database via `_SiteRoutedSession`

### Template URL Generation

Templates must use `site_url()` instead of `url_for()` to preserve the `/site/<key>/` prefix. Exceptions: `url_for('static', ...)` and `url_for('site_manager.*')`.

---

## Database Schema

### Registry Database (`instance/registry.db`)

Managed with raw `sqlite3` (not ORM). Stores site instance metadata.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PK | Auto-increment |
| site_key | TEXT UNIQUE | URL slug (e.g., "charleston") |
| display_name | TEXT | Human-readable market name |
| db_path | TEXT | Path to per-site SQLite DB |
| map_center_lat | REAL | Map center latitude |
| map_center_lon | REAL | Map center longitude |
| map_zoom | INTEGER | Default map zoom level |
| map_bounds_json | TEXT | JSON bounding box |
| zip_codes_json | TEXT | JSON array of supported zip codes |
| target_areas_json | TEXT | JSON area-to-zip mappings |
| active | INTEGER | 1=active, 0=deactivated |
| owner_email | TEXT | Site owner's email |
| pipeline_last_run | TEXT | ISO timestamp |
| listing_count | INTEGER | Cached listing count |
| scheduler_paused | INTEGER | 1=paused |
| created_at | TEXT | ISO timestamp |
| billing_plan | TEXT | Plan tier (e.g., "free", "pro") |
| monthly_budget | REAL | Budget cap in dollars |
| monthly_limit_ai | INTEGER | Max AI calls per billing cycle |
| monthly_limit_fetch | INTEGER | Max fetch calls per billing cycle |
| billing_email | TEXT | Billing contact email |
| billing_cycle_start | TEXT | ISO date of current cycle start |
| landmarks_json | TEXT | JSON array of site landmarks (default '[]'); each entry has name, lat, lng |
| scheduler_locked | INTEGER | 1=master has force-disabled the scheduler; owner cannot override |
| max_fetches_per_run | INTEGER | Max listings the pipeline processes per run (0=unlimited) |

### Per-Site Database Models (ORM)

#### User
| Column | Type | Notes |
|--------|------|-------|
| id | Integer PK | |
| email | String | Not unique (master holds 4 roles on one email) |
| username | String | Unique |
| password_hash | String | bcrypt via werkzeug |
| is_verified | Boolean | Email verified? |
| role | String | `master`\|`owner`\|`agent`\|`client`\|`principal` |
| is_suspended | Boolean | Account suspended by admin |
| suspended_reason | String | Reason for suspension |
| agent_id | FK → AgentProfile | Set for principals only |
| preferences_json | Text | JSON scoring weights, price range, avoid areas, POI keys (`proximity_poi_name`, `proximity_poi_lat`, `proximity_poi_lng`, `imp_proximity_poi`), personal landmarks (`user_landmarks` — array of up to 3 objects with name, lat, lng), `ai_mode` ("off"/"on"/"tune"), `buyer_profile` (dict for AI Tune), `great_deal_threshold` (integer, default 80). Note: `ai_mode`, `buyer_profile`, and `great_deal_threshold` are preserved during scoring preference saves. |
| created_at | DateTime | |
| last_login | DateTime | |

#### AgentProfile
| Column | Type | Notes |
|--------|------|-------|
| id | Integer PK | |
| user_id | FK → User (unique) | 1:1 relationship |
| full_name, license_number, brokerage, phone | String | Professional info |
| bio, service_areas | Text | |
| status | String | `pending`\|`approved`\|`suspended` |
| brand_color, brand_logo_url, brand_icon, brand_tagline | String | Branding |

#### Listing
| Column | Type | Notes |
|--------|------|-------|
| id | Integer PK | |
| source | String | `zillow`\|`realtor` |
| source_id | String (unique) | External listing ID |
| url, address, city, zip_code, area_name | String | Location |
| price | Integer | Listing price |
| beds | Integer | Bedrooms |
| baths | Float | Bathrooms |
| sqft, lot_sqft | Integer | Square footage |
| latitude, longitude | String | Coordinates |
| has_garage, has_porch, has_patio, is_single_story | Boolean | Features |
| flood_zone | String | FEMA zone |
| above_flood_plain | Boolean | |
| year_built, stories | Integer | |
| hoa_monthly | Float | Monthly HOA fee |
| property_tax_annual | Float | Annual tax |
| nearest_hospital_miles, nearest_grocery_miles | Float | Proximity |
| has_community_pool | Boolean | |
| walkability_score | Float | 0–100 |
| price_change_pct | Float | Price trend |
| photo_urls_json | Text | JSON array of image URLs |
| price_history_json | Text | JSON price change history |
| description | Text | Full listing description |
| status | String | `active`\|`pending`\|`sold`\|`delisted` |
| first_seen, last_seen | DateTime | Tracking |

#### DealScore
| Column | Type | Notes |
|--------|------|-------|
| id | Integer PK | |
| listing_id | FK → Listing (unique) | 1:1 |
| price_score, size_score, yard_score, feature_score, flood_score | Float | 0–100 each |
| extended_scores_json | Text | JSON with 12 additional sub-scores |
| composite_score | Float (indexed) | Weighted aggregate |
| scored_at | DateTime | |

#### StreetWatch
| Column | Type | Notes |
|--------|------|-------|
| id | Integer PK | |
| email | String | Notification email |
| user_id | FK → User (nullable) | Linked on registration |
| street_name | String | Normalized uppercase (e.g., "OAK DR") |
| zip_code | String | |
| label | String | Display version (e.g., "Oak Dr") |
| is_active | Boolean | |
| unsubscribe_token | String (unique) | For email unsubscribe |
| UNIQUE | (email, street_name, zip_code) | |

#### StreetWatchAlert
| Column | Type | Notes |
|--------|------|-------|
| id | Integer PK | |
| watch_id | FK → StreetWatch | |
| listing_id | FK → Listing | |
| alert_type | String | `new_listing`\|`price_drop`\|`back_on_market` |
| detail_json | Text | JSON event details |
| emailed_at | DateTime (nullable) | NULL = pending |
| UNIQUE | (watch_id, listing_id, alert_type) | Idempotent |

#### Other Models

- **UserFlag** — Favorite/Maybe/Hidden flags per user per listing
- **ListingNote** — User notes + visit status per listing
- **CachedAnalysis** — Claude AI response cache (deal/portfolio/prefs)
- **AgentClientNote** — Agent's notes on a client (checklists)
- **OwnerAgentNote** — Owner's notes on an agent (contract, background)
- **PromptOverride** — Agent or site-wide AI prompt customization
- **ApiCallLog** — Tracks every external API call with cost estimation

### Migration (`app/migrations.py`)

Idempotent migrations cover 8 social tables: `social_shares`, `social_reactions`, `social_collections`, `social_collection_items`, `referrals`, `user_points`, `user_point_log`, `friend_listings`. Also adds `is_suspended` and `suspended_reason` columns to `users`, and approval columns (`approved_by_agent_id`, `approved_at`, `listing_id`, `rejection_reason`) to `friend_listings`.

#### Social Models (`app/models_social.py`)

- **SocialShare** — Tracks shared listings/collections with recipient, message, share type
- **SocialReaction** — Recipient reactions (love, interested, not_for_me, etc.)
- **SocialCollection** — Curated groups of listings
- **SocialCollectionItem** — Listings within a collection
- **Referral** — Referral attribution chain for new user signups

#### Phase 2 Models (`app/models_social.py`)

##### UserPoints
| Column | Type | Notes |
|--------|------|-------|
| user_id | FK -> User (unique) | 1:1 relationship |
| balance | Integer | Current point balance |
| lifetime_earned | Integer | Total points ever earned |
| updated_at | DateTime | Last balance change |

##### UserPointLog
| Column | Type | Notes |
|--------|------|-------|
| user_id | FK -> User | |
| delta | Integer | Points awarded (positive) or spent (negative) |
| reason | String | Action that earned/spent points |
| reference_id | String | Related object ID (e.g., share ID) |
| created_at | DateTime | |

##### FriendListing
| Column | Type | Notes |
|--------|------|-------|
| submitter_id | FK -> User | User who submitted |
| submitter_email | String | Submitter's email |
| address, city, zip_code | String | Property location |
| price | Integer | Listing price |
| bedrooms, bathrooms | Integer/Float | |
| sqft | Integer | Square footage |
| description | Text | Property description |
| photos_json | Text | JSON array of photo URLs |
| relationship | String | Submitter's relation to property |
| has_permission | Boolean | Permission to list obtained |
| status | String | `active`\|`expired`\|`removed`\|`approved`\|`rejected` |
| created_at | DateTime | |
| expires_at | DateTime | Auto-expiration |
| approved_by_agent_id | FK -> AgentProfile | Reviewing agent |
| approved_at | DateTime | Approval timestamp |
| listing_id | FK -> Listing | Created Listing after approval |
| rejection_reason | String | Reason if rejected |

---

## Scoring System (18 Factors)

Each listing receives 18 sub-scores (0–100). The composite score is a weighted average using the user's importance weights (0–10 scale). The 18th factor (proximity_poi) is per-user -- each user selects their own landmark from site-wide landmarks or their personal landmarks (stored in `user_landmarks` within `preferences_json`, max 3).

**Detail page map:** The listing detail page map displays all landmarks (site-wide + user-defined) as red star icons with hover tooltips. Below the map, a "Directions from [landmark name]" link opens Google Maps with driving directions from the user's selected POI landmark to the listing.

| Factor | Max Score Trigger | Min Score Trigger |
|--------|-------------------|-------------------|
| price | Sweet spot ~70% of max budget | Over budget |
| size | ≥ 3,000 sqft | < 1,200 sqft |
| yard | ≥ 20,000 lot sqft | < 5,000 lot sqft |
| features | Garage + porch + patio + 4bd/3ba | No features, low bed/bath |
| flood | Above flood plain | In X flood zone |
| year_built | 2020+ | Pre-1960 |
| single_story | Single story confirmed | 3+ stories |
| price_per_sqft | ≤ $120/sqft | ≥ $275/sqft |
| days_on_market | < 7 days (fresh) | > 60 days (stale) |
| hoa | No HOA or $0 | ≥ $500/mo |
| proximity_medical | < 1 mile to hospital | > 10 miles |
| proximity_grocery | < 0.5 miles | > 2 miles |
| community_pool | Yes | No |
| property_tax | Low rate relative to price | High rate |
| lot_ratio | Lot ≥ 2× house sqft | Lot < 0.5× house |
| price_trend | Price dropped | Price increased |
| walkability | High walkability score | Low score |
| proximity_poi | 0–1 miles from landmark | 15+ miles from landmark |

**Composite formula:**
```
composite = Σ (sub_score × importance[factor]) / Σ importance[factor]
```

Each user's composite is recalculated on-demand using their personal weights and price range.

---

## API Integrations

### RapidAPI — Zillow & Realtor
- **Zillow:** `realty-in-us.p.rapidapi.com` — search by zip, property details
- **Realtor:** Similar endpoints, cross-referencing data source
- **Rate limiting:** Tracked in `ApiCallLog` with quota monitoring

### Anthropic — Claude AI
- **Model:** Claude Sonnet 4 (`claude-sonnet-4-20250514`)
- **Uses:** Deal briefs, portfolio analysis, preference coaching
- **Caching:** Results stored in `CachedAnalysis` table
- **Prompts:** Overridable per-agent and per-site via `PromptOverride`

### Geoapify — Street Autocomplete
- **Endpoint:** `/v1/geocode/autocomplete`
- **Called:** Client-side from browser JavaScript (no server proxy)
- **Optimization:** Circle filter (25km radius) around site map center
- **Fallback:** Local listing DB search when no API key configured

### Census TIGER/Line
- **Purpose:** Assign Census-defined place names to listings
- **Method:** Point-in-polygon against shapefile geometries
- **Data:** `data/tl_2024_45_place/tl_2024_45_place.shp` (SC only)

### Points Service (`app/services/points.py`)
- `award_points(user_id, delta, reason, reference_id)` — Award points with daily cap enforcement
- `get_balance(user_id)` — Current point balance
- `DAILY_CAP = 50` — Maximum points earnable per day
- `POINT_VALUES` dict — Point values by action type

### Billing Service (`app/services/billing.py`)
- `check_quota(site_key, call_type)` — Pre-flight check before API calls
- `get_site_usage(site_key)` — Current cycle usage stats
- `get_billing_info(site_key)` — Plan details and limits
- `send_budget_alert(site_key, pct)` — Alert when approaching budget limit
- `PLAN_DEFAULTS` dict — Default quotas per plan tier

### Social Digest Service (`app/services/social_digest.py`)
- `send_weekly_digests(site_key)` — Compile and send weekly social activity summaries

---

## Pipeline

### Flow

```
1. Fetch     → Zillow + Realtor APIs for all site zip codes
2. Pre-Dedup → Normalize addresses + merge richer data per field
3. Upsert    → Create new or update existing Listing rows
4. Track     → Maintain price_history_json for changes
5. Score     → Compute 18-factor deal scores
6. Post-Dedup→ deduplicate_existing() marks DB duplicates as status="duplicate"
7. Geocode   → Assign Census place names (SC)
8. Watch     → Detect events (new, price drop, back on market)
9. Digest    → Send Street Watch email alerts
```

### Deduplication

Two layers of deduplication run during each pipeline execution:

1. **Pre-upsert dedup** (`_deduplicate_listings()`) — Normalizes addresses via `_normalize_address()` (lowercase, strip punctuation, expand abbreviations like St to Street, Rd to Road, N to North, etc.), groups by normalized address, and merges duplicates via `_merge_listing_data()` (richer data wins per field: more photos, longer description, True beats False for boolean features).

2. **Post-upsert DB cleanup** (`deduplicate_existing()`) — Runs after every pipeline, finds existing duplicate listings in the database by normalized address, merges richer data into the keeper, and marks duplicates as `status="duplicate"`.

### Detail Page Enrichment (AJAX)

Enrichment is no longer a blocking call on page load. The detail page renders instantly and shows a **"Fetch Property Details"** button if the listing lacks enrichment data. The button triggers an AJAX POST to `/listing/<id>/enrich`, which fetches details from Zillow/Realtor. The endpoint returns JSON with updated fields. HTTP status codes: 200 (success), 429 (quota exceeded), 503 (API unavailable).

### Scheduling

- **Production:** Windows Task Scheduler runs `bin/scheduled_pipeline.py` nightly at 3 AM
- **Manual:** Owner/master can trigger via dashboard button (`/fetch-now`)
- **CLI:** `python pipeline.py --site charleston [--rescore]`

### Watch Event Detection

During upsert, the pipeline detects:
- **new_listing** — listing ID not previously in DB
- **price_drop** — `price < previous_price`
- **back_on_market** — status changed back to `active`

Events are matched against active StreetWatch records and queued as StreetWatchAlert rows, then emailed in batch.

---

## Deployment

### IIS + Waitress

```
IIS HttpPlatformHandler → python.exe run_waitress.py --port=%HTTP_PLATFORM_PORT%
```

- **Threads:** 4
- **URL prefix:** `/home_finder_agents`
- **URL scheme:** `https`
- **Security:** `.env`, `instance/`, `__pycache__`, `.venv` hidden; `.py`, `.db` blocked

### App Pool Recycling

After any Python, template, or config change:

```powershell
appcmd.exe recycle apppool /apppool.name:HomeFinderAgents
```

Browser hard-refresh: **Ctrl+Shift+R** (for template/static changes)

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| SECRET_KEY | Yes | Flask session encryption key |
| RAPIDAPI_KEY | Yes | Zillow/Realtor API access |
| ANTHROPIC_API_KEY | Yes | Claude AI deal analysis |
| MAIL_SERVER | Yes | SMTP server (e.g., smtp.gmail.com) |
| MAIL_PORT | Yes | SMTP port (587 for TLS) |
| MAIL_USERNAME | Yes | Sender email address |
| MAIL_PASSWORD | Yes | SMTP password / app password |
| GEOAPIFY_KEY | No | Street autocomplete (free tier: 90K/mo) |
| GOOGLE_MAPS_KEY | No | Optional maps integration |

---

## Route Reference

### Authentication (`/auth`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET, POST | `/auth/register` | Account registration with email verification |
| GET, POST | `/auth/login` | Login with role-priority resolution |
| GET | `/auth/logout` | Session destruction |
| GET | `/auth/verify/<token>` | Email verification |
| GET, POST | `/auth/resend-verification` | Resend verification email |
| GET, POST | `/auth/forgot-password` | Password reset request |
| GET, POST | `/auth/reset-password/<token>` | Password reset |
| GET, POST | `/auth/agent-signup` | Agent registration |
| POST | `/auth/masquerade/<user_id>` | Impersonate user |
| GET | `/auth/end-masquerade` | End impersonation |
| GET, POST | `/auth/close-account` | Delete account |

### Dashboard (`/`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/welcome` | Market selector |
| GET | `/` | Listing grid with filters and scores |
| GET | `/listing/<id>` | Property detail page |
| POST | `/listing/<id>/enrich` | AJAX detail enrichment from Zillow/Realtor |
| POST | `/listing/<id>/flag` | Toggle flag (AJAX) |
| POST | `/listing/<id>/note` | Save notes (AJAX) |
| POST | `/listing/<id>/analyze` | AI deal brief (AJAX) |
| GET | `/map` | Interactive map |
| GET | `/digest` | Email-style summary |
| GET, POST | `/preferences` | Scoring weights editor; owners see target area labeling; masters see all zips with `canAddZips` to add/remove from site |
| POST | `/analyze-portfolio` | AI portfolio analysis |
| POST | `/analyze-preferences` | AI preference coaching |
| GET | `/agent/dashboard` | Agent client roster |
| POST | `/fetch-now` | Manual pipeline trigger |
| GET | `/admin/metrics` | Usage metrics |
| GET | `/admin/agents` | Agent management |
| GET, POST | `/admin/prompts` | Prompt overrides |
| POST | `/admin/prompts/validate` | Validate prompt syntax (AJAX, admin) |
| POST | `/admin/prompts/preview` | Test prompt with sample data (AJAX, admin) |
| GET | `/admin/users` | User management page |
| POST | `/admin/users/<id>/action` | Suspend/reactivate/delete user |
| GET, POST | `/admin/billing` | Billing settings |
| GET, POST | `/agent/add-listing` | Agent direct listing creation |
| GET, POST | `/agent/friend-listing/<id>/review` | Review/edit friend listing |
| POST | `/agent/friend-listing/<id>/approve` | Approve and create Listing |
| POST | `/agent/friend-listing/<id>/reject` | Reject with reason |
| POST | `/my-landmarks` | Add/delete user-defined personal landmarks (AJAX, auth required, max 3) |
| POST | `/admin/landmarks` | Add/delete site landmarks (AJAX, owner/master) |
| GET | `/settings` | Settings page with Help Level, Power Mode, and AI Analysis cards |
| POST | `/api/ai-mode` | Set AI mode ("off"/"on"/"tune") and save buyer profile (AJAX) |
| POST | `/api/buyer-profile` | Save buyer profile for AI Tune (AJAX) |

### Street Watch (`/watch`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/watch` | Watch management page |
| POST | `/watch/quick` | Create watch (AJAX, auth required) |
| GET | `/watch/streets` | Street autocomplete (AJAX) |
| POST | `/watch/remove/<id>` | Remove watch (AJAX) |
| GET | `/watch/unsubscribe/<token>` | Email unsubscribe |

### Social (`/social`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/social/points` | Points history page |
| GET | `/social/leaderboard` | Monthly leaderboard |
| GET, POST | `/social/add-home` | Friend listing submission form |
| GET | `/social/friend-listings` | Browse active friend listings |
| POST | `/social/send-digest` | Trigger weekly digest (owner/master) |

### Site Manager (`/admin/sites`) — Master only
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/admin/sites` | List all markets |
| POST | `/admin/sites/create` | Create new market (seeds agent profiles + principal links) |
| POST | `/admin/sites/<key>/edit` | Update market config |
| POST | `/admin/sites/<key>/toggle` | Activate/deactivate |
| POST | `/admin/sites/<key>/delete` | Delete market |

---

## Authentication & Masquerade

### Role-Priority Login

When a user logs in with an email address (rather than a username), the login route queries all accounts sharing that email and selects the one with the highest role. Priority order: `master` > `owner` > `agent` > `principal` > `client` > `user`. If the user types a specific username, that exact account is used regardless of role priority.

### Context Processor: `inject_siblings`

A context processor registered in `create_app()` that makes `sibling_accounts` available in all templates. For master users who are not currently masquerading, it queries all accounts sharing the same email and returns them sorted by role priority. The navbar user dropdown uses this to render the "Switch Role" section with role badges and colored icons.

### Chained Masquerade

The masquerade system supports one level of chaining: master -> agent -> principal.

- `POST /auth/masquerade/<user_id>` sets `session['masquerade_original_id']` only on the first hop. If the key already exists (i.e., this is a second hop), it is not overwritten.
- `GET /auth/end-masquerade` always restores `session['masquerade_original_id']` (the true original user) and clears the key -- regardless of how many hops occurred.
- This means a master masquerading as an agent can use the agent's "Preview" button to masquerade as a principal, and "End Preview" returns directly to the master.

### Settings Page

The Settings page (`GET /settings`) provides a unified interface with three cards:

1. **Help Level** — slider (1–3) controlling the verbosity of contextual help throughout the UI
2. **Power Mode** — off/low/high toggle controlling advanced feature visibility
3. **AI Analysis** — off/on/tune selector; "tune" reveals the Buyer Profile form for AI Tune personalization

Settings are persisted in `preferences_json` for authenticated users and in the session for guests.

### Navigation

- The **Help** nav item is a direct link to the Help page (no longer a dropdown menu)
- Active nav items use a **nav-active underline indicator** system implemented via CSS custom properties (`--nav-active-color`)
- The **Settings** gear icon in the nav links to the Settings page

### Nearest-to-Me Sort (Removed)

The "Nearest to Me" sort option has been removed from the dashboard sort dropdown.

### Manage Dropdown & Cross-Site Login

Master users see a **Manage** dropdown in the nav that consolidates the former separate "Sites" and "Manage" nav items. Clicking a site triggers the `go_to_site` route, which performs cross-site login by looking up the user's email in the target site's database and logging in as the matching account. This email-based user ID remapping is necessary because user IDs differ across per-site SQLite databases.

### AJAX Flag Toggle

The flag toggle endpoint (`POST /listing/<id>/flag`) returns JSON for authenticated users, allowing the dashboard to update flag icons without a page reload. Guest flag toggles continue to use session-based storage.

### Feedback Button

The Feedback button requires authentication and `power_mode != 'low'`. It uses an `onclick` JavaScript handler to open the feedback modal rather than Bootstrap's `data-bs-toggle` attribute.

---

## Dependencies

**Core:** Flask, Flask-SQLAlchemy, Flask-Login, Flask-Mail, Waitress, python-dotenv
**AI:** anthropic (Claude SDK)
**Data:** geopandas, shapely (Census geocoding)
**APIs:** requests (RapidAPI), Geoapify (client-side JS)
**Auth:** werkzeug.security (bcrypt), itsdangerous (token serialization)
**Test:** pytest

---

## Engagement Features

Three reciprocity-based features drive user engagement across all roles:

### 1. "Since Your Last Visit" Card

**Route:** `index()` in `app/routes/listings.py` (lines 203–231)
**Template:** `dashboard/index.html`

For authenticated users with `last_login`, queries `Listing` for:
- `first_seen > last_login` → new listings count
- `price_change_pct < 0 AND last_seen > last_login` → price drop count

Guests receive `total_scored` and `top_score` to demonstrate platform value.

### 2. Progressive Flagging Milestones

**Route:** `toggle_flag()` in `app/routes/listings.py` (lines 455–493)

After each favorite flag, queries `UserFlag.count()` and flashes context-aware messages:
- **1st favorite:** "Great first pick!"
- **3rd favorite:** Suggests AI Portfolio Analysis (includes agent name if principal)
- **5th favorite:** Suggests Tour planning (agent-specific if applicable)
- **Guest 1st:** Session persistence notice
- **Guest 3rd:** Account creation nudge with register link

### 3. Smart Empty States

All "nothing here" empty states replaced with value-first messaging across 9 templates:

| Template | Empty State Message |
|----------|-------------------|
| `digest.html` | Suggests broadening filters + browse link |
| `watch.html` | Explains Street Watch value + browse link |
| `index.html` | Agent encouragement for principals |
| `itinerary.html` | Agent encouragement for principals |
| `welcome.html` | "Adding new markets" + account prompt |
| `landing.html` | "Setting up markets" + signup prompt |
| `admin_agents.html` | "All caught up" / agent signup link |
| `admin_metrics.html` | Explains when costs appear |
| `agent_dashboard.html` | Explains client onboarding experience |

---

## Test Suite

**Location:** `tests/`
**Runner:** `python -m pytest tests/ -v`

| File | Coverage |
|------|----------|
| `test_models.py` | User, AgentProfile, Listing, UserFlag models |
| `test_auth.py` | Registration, login, verification, agent guards, masquerade, close account |
| `test_scoring.py` | DealScore composite, user weights, zero weights, 18-factor validation |
| `test_street_watch.py` | Extraction, CRUD, deactivation, token unsubscribe, watch linking |
| `test_engagement.py` | Since-last-visit stats, progressive nudges, smart empty state content |
| `test_social_phase2.py` | Points system, referral loops, social models, agent listing workflow, user suspension, share counts/social proof, collections |
| `test_ai_tune.py` | AI Tune settings, buyer profile persistence, ai_mode transitions |
| `test_great_deal.py` | Great Deal threshold, badge rendering, visual effects |
| `test_session.py` | Session handling, guest state management |
| `test_session2.py` | Extended session tests, cross-site login, flag toggle AJAX |

**Fixtures** (`conftest.py`): Creates a temporary registry + site DB per test, with helpers `make_user()`, `make_listing()`, `make_agent_profile()`.

**Total: ~240 tests across 11 files**
