# HomeFinder — Architecture Guide

**Version:** 2026.03.14
**Last Updated:** 2026-03-14

---

## System Architecture

```
                    ┌─────────────┐
                    │   Browser   │
                    └──────┬──────┘
                           │ HTTPS
                    ┌──────┴──────┐
                    │     IIS     │
                    │ (reverse    │
                    │  proxy)     │
                    └──────┬──────┘
                           │ HTTP (localhost)
                    ┌──────┴──────┐
                    │  Waitress   │
                    │ (WSGI, 4    │
                    │  threads)   │
                    └──────┬──────┘
                           │
              ┌────────────┴────────────┐
              │      Flask App          │
              │  ┌───────────────────┐  │
              │  │SitePathMiddleware │  │ ← extracts /site/<key>/
              │  └────────┬──────────┘  │
              │  ┌────────┴──────────┐  │
              │  │  select_site()    │  │ ← binds g.site + g.site_engine
              │  └────────┬──────────┘  │
              │  ┌────────┴──────────┐  │
              │  │   Blueprints      │  │
              │  │  ├ dashboard (/)   │  │
              │  │  ├ auth (/auth)   │  │
              │  │  ├ social (/social)│  │
              │  │  ├ site_mgr       │  │
              │  │  └ docs (/docs)   │  │
              │  └───────────────────┘  │
              └────────────┬────────────┘
                    ┌──────┴──────┐
          ┌─────────┤  Databases  ├─────────┐
          │         └─────────────┘         │
    ┌─────┴──────┐               ┌──────────┴───────┐
    │registry.db │               │ Per-Site DBs      │
    │(raw sqlite3)│              │ charlestonsc.db   │
    │ - sites    │               │ catonsvillemd.db  │
    │ - config   │               │ (ORM-managed)     │
    │ - landmarks│               │                   │
    └────────────┘               └──────────────────┘
```

---

## Multi-Tenancy

### The Problem

HomeFinder serves multiple real estate markets (Charleston, Catonsville, etc.) from a single deployment. Each market needs:
- Its own set of listings, users, and configurations
- Independent data pipelines
- Isolated databases (no cross-market data leaks)

### The Solution: Path-Based Tenant Routing

```
URL: /home_finder_agents/site/charleston/preferences
                          ^^^^^^^^^^^^
                          tenant key extracted by middleware
```

**SitePathMiddleware** (WSGI level):
1. Matches `/site/<key>/` in the URL path
2. Sets `HTTP_X_HOMEFINDER_SITE` header
3. Strips the `/site/<key>/` segment so Flask sees clean routes
4. If no site segment and user has a session site, redirects

**select_site()** (before_request):
1. Reads site key from header
2. Looks up site config in `registry.db`
3. Creates/caches a SQLAlchemy engine for the site's SQLite file
4. Sets `g.site` (dict with config) and `g.site_engine` (engine)

**_SiteRoutedSession** (ORM layer):
1. Wraps SQLAlchemy session
2. Overrides `get_bind()` to return `g.site_engine`
3. All ORM queries transparently go to the correct database

### Engine Caching

Per-site SQLAlchemy engines are cached in a module-level dict keyed by `db_path`. This avoids creating new engine connections on every request while still routing correctly.

---

## Application Factory

`app/__init__.py` → `create_app()`:

```python
def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Extensions
    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    migrate.init_app(app)

    # Multi-tenant middleware
    app.wsgi_app = SitePathMiddleware(app.wsgi_app)

    # Blueprints
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(social_bp, url_prefix="/social")
    app.register_blueprint(site_manager_bp, url_prefix="/admin/sites")
    app.register_blueprint(docs_bp, url_prefix="/docs")

    # Context processors (site_url, current_site, app_version)
    # Before-request hooks (select_site, request_logger)
    # Jinja filters (from_json)

    return app
```

---

## Blueprint Architecture

### Dashboard Blueprint (`/`)

The largest blueprint, handling all user-facing functionality. Split across multiple files imported into `dashboard.py`:

```
app/routes/
  ├─ dashboard.py          # Blueprint registration + imports
  ├─ listings.py           # Listing grid, detail, flag, note
  ├─ preferences_routes.py # Scoring weight editor
  ├─ ai_routes.py          # Claude AI analysis endpoints
  ├─ agent_routes.py       # Agent dashboard, client management
  ├─ admin_routes.py       # Owner/master admin pages
  ├─ tour_routes.py        # Tour planning
  ├─ watch_routes.py       # Street Watch
  └─ dashboard_helpers.py  # Shared utilities
```

All route files register on `dashboard_bp` — they import it and decorate their routes.

### Auth Blueprint (`/auth`)

Self-contained authentication module:
- Registration with email verification
- Login/logout with remember-me
- Password reset flow
- Agent registration
- Masquerade (impersonation) for agents and owners

### Site Manager Blueprint (`/admin/sites`)

Master-only interface for managing market instances:
- CRUD operations on `registry.db`
- Map picker for setting site center and zip codes
- Database initialization for new sites

### Social Blueprint (`/social`)

Social sharing, gamification, and community features:
- Points system with daily cap and leaderboard
- Friend listing submissions with agent review workflow
- Weekly social digest emails
- Sharing, reactions, collections, referrals

### Docs Blueprint (`/docs`)

Master-only documentation viewer and editor.

---

## Data Flow

### Listing Lifecycle

```
RapidAPI (Zillow/Realtor)
    │
    ▼
Pipeline fetch     ← bin/scheduled_pipeline.py (nightly)
    │                 or /fetch-now (manual)
    ▼
Dedup + Upsert     ← match by source_id
    │
    ▼
Score (18 factors)  ← app/scraper/scorer.py
    │
    ▼
Place geocode       ← Census TIGER/Line (SC only)
    │
    ▼
Watch events        ← detect new/price_drop/back_on_market
    │
    ▼
Alert emails        ← StreetWatchAlert → digest email
```

### User Interaction Flow

```
User loads dashboard
    │
    ▼
Fetch listings      ← ORM query with filters
    │
    ▼
Compute user scores ← DealScore.compute_user_composite(prefs)
    │
    ▼
Render template     ← Jinja2 with site_url() helper
    │
    ▼
AJAX interactions   ← Flag, note, analyze (JSON endpoints)
```

### AI Analysis Flow

```
User clicks "Analyze"
    │
    ▼
Check CachedAnalysis ← return cached if fresh
    │ (miss)
    ▼
Build AI context     ← ai_context.py compiles listing + scores + prefs
    │
    ▼
Resolve prompt       ← PromptOverride: agent → site → default
    │
    ▼
Call Claude API      ← anthropic SDK
    │
    ▼
Parse response       ← JSON extraction
    │
    ▼
Cache result         ← CachedAnalysis.save()
    │
    ▼
Log API call         ← ApiCallLog
    │
    ▼
Return to user
```

### Points Earning Flow

```
User action (share, react, refer, submit friend listing)
    |
    v
award_points()          <- app/services/points.py
    |
    v
Check DAILY_CAP (50)    <- sum today's UserPointLog
    |
    v
Insert UserPointLog     <- delta, reason, reference_id
    |
    v
Update UserPoints       <- increment balance + lifetime_earned
```

### Billing Quota Check Flow

```
API call requested (AI analysis, pipeline fetch)
    |
    v
check_quota()           <- app/services/billing.py
    |
    v
Read registry.db        <- billing_plan, monthly_limit_*
    |
    v
Count ApiCallLog        <- current cycle usage
    |
    v
Allow / deny            <- return True/False
    |
    v
send_budget_alert()     <- if usage >= 80% threshold
```

### Friend Listing Approval Flow

```
User submits friend listing  <- /social/add-home
    |
    v
FriendListing created        <- status='active', expires_at set
    |
    v
Agent reviews                <- /agent/friend-listing/<id>/review
    |
    v
Approve or Reject
    |                    |
    v                    v
Create Listing row     Set status='rejected'
Set status='approved'  Record rejection_reason
Link listing_id
```

---

## Session & Authentication

### Flask-Login Integration

```python
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
```

### Masquerade

Agents and owners can impersonate users:

```python
session['masquerade_original_id'] = current_user.id
login_user(target_user)
```

The original identity is preserved in the session. A visible banner shows masquerade status. `end_masquerade` restores the original user.

**Scope:**
- Agents → own clients only
- Owners → any user in the site
- Master → any user in any site

### Guest Support

Unauthenticated users can browse and flag:
- `session["guest_flags"]` — dict of listing_id → flag
- `session["guest_prefs"]` — scoring preferences
- `session["guest_analyses"]` — cached AI results

On registration, guest data can be migrated to the new account.

---

## Template System

### Context Processors

Every template has access to:
- `current_site` — registry dict for the active market
- `site_url(endpoint, **kwargs)` — generates URLs with `/site/<key>/` prefix
- `app_version` — current app version string
- `current_user` — Flask-Login user object

### site_url() vs url_for()

```jinja
{# CORRECT — preserves multi-tenant context #}
<a href="{{ site_url('dashboard.index') }}">Dashboard</a>

{# WRONG — loses site context #}
<a href="{{ url_for('dashboard.index') }}">Dashboard</a>

{# EXCEPTION — static files don't need site context #}
<link href="{{ url_for('static', filename='css/style.css') }}">
```

---

## Error Handling

### Pipeline Errors
- Pipeline failures are logged but never crash the web server
- Street Watch processing is wrapped in try/except — failures don't block the main fetch/score cycle
- API failures fall back gracefully (e.g., Geoapify → local DB search)

### Database Errors
- Each request gets its own session via `_SiteRoutedSession`
- Failed transactions are rolled back per-request
- SQLite WAL mode enables concurrent readers

### API Rate Limiting
- All external API calls are logged in `ApiCallLog`
- Quota tracking via `quota_remaining` field
- Diagnostics page surfaces rate limit issues

---

## File Structure

```
home_finder_agents/
├── app/
│   ├── __init__.py          # Factory, middleware, multi-tenant routing
│   ├── models.py            # 11 ORM models + is_suspended fields
│   ├── models_social.py     # Social models (shares, reactions, collections, referrals, points, friend listings)
│   ├── migrations.py        # Idempotent schema migrations (8 social tables)
│   ├── utils.py             # site_url, site_redirect helpers
│   ├── routes/
│   │   ├── dashboard.py     # Blueprint + route imports
│   │   ├── listings.py      # Listing grid, detail, flag, note
│   │   ├── auth.py          # Authentication flows
│   │   ├── social_routes.py # Social sharing, points, friend listings
│   │   ├── site_manager.py  # Site CRUD (master)
│   │   ├── docs.py          # Documentation viewer
│   │   ├── ai_routes.py     # Claude AI endpoints
│   │   ├── agent_routes.py  # Agent dashboard
│   │   ├── admin_routes.py  # Owner/master admin
│   │   ├── watch_routes.py  # Street Watch
│   │   ├── tour_routes.py   # Tour planning
│   │   └── preferences_routes.py
│   ├── scraper/
│   │   ├── pipeline.py      # Orchestrator
│   │   ├── zillow.py        # Zillow RapidAPI
│   │   ├── realtor.py       # Realtor RapidAPI
│   │   ├── scorer.py        # 18-factor scoring (includes proximity POI)
│   │   ├── geocoder.py      # Address geocoding
│   │   └── scheduler.py     # (legacy, replaced by Task Scheduler)
│   ├── services/
│   │   ├── deal_analyst.py  # Claude AI integration
│   │   ├── ai_context.py    # AI prompt context builder
│   │   ├── registry.py      # Registry.db CRUD
│   │   ├── place_geocoder.py # Census TIGER/Line
│   │   ├── street_watch.py  # Street monitoring logic
│   │   ├── points.py        # Points system (award, balance, daily cap)
│   │   ├── billing.py       # Quota checks, budget alerts
│   │   └── social_digest.py # Weekly social digest emails
│   ├── templates/           # 45+ Jinja2 templates
│   └── static/              # CSS, JS, images
├── instance/                # SQLite databases (gitignored)
├── data/                    # Census shapefiles
├── bin/                     # CLI scripts
├── docs/                    # Documentation
├── config.py                # Configuration + defaults
├── wsgi.py                  # WSGI entry point
├── run_waitress.py          # Waitress launcher
├── web.config               # IIS configuration
└── pipeline.py              # CLI pipeline entry point
```
