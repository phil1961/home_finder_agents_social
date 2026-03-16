<!-- v20260309-1 -->
# HomeFinder

A multi-tenant real estate listing discovery and scoring platform. Buyers find deals, agents manage clients, owners manage their market, and a master operator runs all markets from a single deployment.

**Production:** https://www.toughguycomputing.com/home_finder_agents/  
**Operator:** Phil Larson / Marvin-Medisoft

---

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt
pip install apscheduler

# Copy and configure environment
copy .env.example .env
# Edit .env — set RAPIDAPI_KEY, SECRET_KEY, ANTHROPIC_API_KEY, MAIL_USERNAME, MAIL_PASSWORD

# Run locally
activate.bat
python run_waitress.py
```

Visit `http://localhost:5000/home_finder_agents/welcome` to see the site selector.  
Visit `http://localhost:5000/home_finder_agents/site/charleston/` for the Charleston market.

---

## Multi-Site Access

Each market is a fully isolated HomeFinder instance accessed via URL:

```
/home_finder_agents/welcome              → Site selector (all markets, no auth required)
/home_finder_agents/site/charleston/     → Charleston, SC
/home_finder_agents/site/dayton/         → Dayton, OH
/home_finder_agents/site/<sitekey>/      → Any registered site
```

Without a `/site/<key>/` prefix, requests fall back to the default site (first active site in registry). The `/welcome` route reads the registry directly and is not bound to any site.

---

## User Roles

| Role | Who | Access |
|------|-----|--------|
| `master` | Operator (Phil) | Everything — creates and manages all sites |
| `owner` | Site admin | Admin, Metrics, Prompts, manual Fetch |
| `agent` | Real estate agent | Client management, branding, Prompts |
| `user` | Home buyer | Dashboard, favorites, notes, preferences |
| `user` + `agent_id` | Agent-managed client | Same as user; prefs set by agent |

The master operator has **four accounts** in every site DB (all `philipalarson@gmail.com`), one per role, for full testing at every permission level. These are seeded automatically when a new site is created.

---

## Running the Pipeline

Fetch and score listings for a specific market:

```bash
activate.bat
python pipeline.py --site charleston
python pipeline.py --site dayton
python pipeline.py --site charleston --rescore   # re-score only, skip fetching
```

The nightly APScheduler job runs all active sites automatically at 3:00 AM.

---

## Adding a New Market

1. Log in as master → click **Sites** in the nav
2. Click **Location Picker** and search for a city — auto-fills site key, display name, map center, bounding box, and first zip code
3. Click **Pick Zips** to add more zip codes by clicking colored polygon boundaries on the map
4. Click **Pick on Map** to refine the bounding box if needed
5. Click **Create Site & Initialize Database**
6. All four operator accounts are automatically copied into the new site's DB
7. Run the pipeline: `python pipeline.py --site <sitekey>`
8. Access at: `.../home_finder_agents/site/<sitekey>/`

---

## Key Features

**For Buyers**
- 18-factor deal score (0–100) on every listing, personalized to each user's importance weights
- Target area builder — assign zip code groups to named areas on an interactive map
- Avoid Areas — exclude Census-defined places from the dashboard
- Flag listings as Favorite / Maybe / Hidden; flags persist for guests in session
- Per-listing private notes with visit, offer, and interest tracking
- AI Deal Analyst — per-listing negotiation advice and opening offer suggestions
- AI Portfolio Analysis — ranked comparison of all favorited listings
- AI Preference Feedback — analysis of how preferences interact with current inventory
- Tour Planner — select listings and open a multi-stop Google Maps route

**For Agents**
- Client roster with pre-approval, buyer agreement tracking, and private notes
- Set scoring preferences on behalf of clients
- Custom navbar branding (color, logo, icon, tagline) shown to all linked clients
- Custom AI prompt overrides for the Deal Analyst
- Masquerade as any client to preview their experience

**For Owners**
- Manual pipeline trigger (Fetch Now button)
- Metrics dashboard (listing counts, score distribution, API call log)
- Agent roster with background check / MLS verification tracking
- Custom AI prompt overrides

**For Master**
- Full site registry management from `/admin/sites`
- Location Picker, ZIP polygon picker, and map bounds picker for fast site setup
- Create, edit, activate/deactivate, and delete market instances
- IIS/Nginx config snippet generation per site
- Masquerade as any user in any site

---

## Data Sources

| Source | API | Notes |
|--------|-----|-------|
| Zillow | `us-property-data` on RapidAPI | Better metro coverage; 202 errors on rural zips |
| Realtor.com | `realty-in-us` on RapidAPI | Better rural/small-market coverage |
| Census TIGER/Line | Local shapefile | Place name assignment for Avoid Areas (SC only) |
| Anthropic Claude | `claude-sonnet-4-20250514` | AI Deal Analyst, Portfolio Analysis, Preference Feedback |
| OpenDataDE | GitHub GeoJSON | State zip code polygon boundaries for site setup picker |
| Nominatim / OSM | REST API | Geocoding and reverse geocoding in map pickers |

---

## Environment Variables

```
RAPIDAPI_KEY          RapidAPI key — Zillow + Realtor scrapers
SECRET_KEY            Flask session secret
ANTHROPIC_API_KEY     Claude API key
GOOGLE_MAPS_KEY       Google Maps API key (reserved — not yet wired to embeds)
MAIL_SERVER           SMTP host (default: smtp.gmail.com)
MAIL_PORT             SMTP port (default: 587)
MAIL_USE_TLS          TLS flag (default: true)
MAIL_USERNAME         SMTP login
MAIL_PASSWORD         SMTP password / app password
MAIL_DEFAULT_SENDER   From address
DATABASE_URL          Fallback DB URI (default: charlestonsc.db)
HOMEFINDER_REGISTRY   Override registry.db path (optional)
FETCH_INTERVAL_HOURS  Pipeline interval hint (default: 6)
```

---

## Tech Stack

- **Python 3.12** / Flask / Flask-SQLAlchemy / Flask-Login / Flask-Mail
- **SQLite** — one DB per market (`instance/<sitekey>.db`) plus `instance/registry.db`
- **Waitress** — production WSGI server
- **IIS** — httpPlatformHandler; `web.config` passes all traffic to Waitress
- **APScheduler** — nightly pipeline scheduling (3:00 AM)
- **Bootstrap 5.3** + Bootstrap Icons 1.11
- **Leaflet.js** — interactive maps (preferences zip picker + admin site pickers)
- **OpenStreetMap / Nominatim** — map tiles and geocoding
- **OpenDataDE GeoJSON** — US state zip code polygon boundaries
- **itsdangerous** — signed tokens for email verification and password reset

---

## Project Structure

```
app/
  __init__.py          App factory, SitePathMiddleware, _SiteRoutedSession, APScheduler
  models.py            ORM models: User, AgentProfile, Listing, DealScore, UserFlag,
                         ListingNote, ApiCallLog, CachedAnalysis, AgentClientNote,
                         OwnerAgentNote, PromptOverride
  routes/
    dashboard.py       All buyer/owner/agent routes (~1500 lines)
    auth.py            Register, login, logout, verify, reset, masquerade, agent-signup
    site_manager.py    /admin/sites CRUD — master only
  scraper/
    pipeline.py        Fetch → upsert → geocode → place_name → score → commit
    zillow.py          Zillow RapidAPI scraper
    realtor.py         Realtor.com RapidAPI scraper
    scorer.py          18-factor deal score algorithm
    geocoder.py        Coordinate geocoding fallback
  services/
    registry.py        Registry DB CRUD (raw sqlite3, WAL mode, timeout=10)
    place_geocoder.py  Census TIGER/Line shapefile → place_name lookup
  templates/
    base.html          Shared nav, branding, welcome modal, site_url() context
    admin_sites.html   Site management (master only) — v20260307-8
    auth/              Login, register, verify, reset, welcome email templates
    dashboard/         All buyer/agent/owner page templates
instance/              Runtime databases — gitignored
data/                  Census shapefiles (tl_2024_45_place for SC)
config.py              Flask Config class + global pipeline constants
pipeline.py            CLI entry point
run_waitress.py        Production WSGI launcher
run.py                 Dev server launcher
web.config             IIS httpPlatformHandler configuration
```

See **CONTEXT.md** for full developer reference: patterns, route map, model details, scoring breakdown, picker implementation details, and known issues.
