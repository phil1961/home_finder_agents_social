<!-- v20260315b -->
# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

HomeFinder Social is a multi-tenant Flask web application for real estate listing discovery with AI-powered deal scoring and social sharing features. Each market (site) has its own SQLite database; a central registry tracks all sites. Features include 18-factor deal scoring, Claude AI deal analysis, agent/client management, tour planning, interactive maps, social listing sharing with referral tracking, a points/gamification system, friend listings, billing tiers, and social digest emails.

**Live URL:** `https://www.toughguycomputing.com/home_finder_agents_social/`

## Running Locally

```bash
cd D:\Projects\home_finder_agents_social
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
# Edit .env: set RAPIDAPI_KEY, SECRET_KEY, ANTHROPIC_API_KEY, MAIL_* vars
python run_waitress.py
# Visit http://localhost:8080/home_finder_agents_social/welcome
```

Run the data pipeline:
```bash
python pipeline.py --site charleston          # fetch + dedup + score
python pipeline.py --site charleston --rescore # re-score only
```

## Architecture

**Multi-tenant routing:** `SitePathMiddleware` in `app/__init__.py` extracts site key from URL path (`/site/<key>/...`), sets `g.site` with registry data, and binds `g.site_engine` to the correct per-site SQLite database. `_SiteRoutedSession` wraps SQLAlchemy sessions to transparently route all ORM queries to the current site's DB.

**Registry:** `instance/registry.db` (raw sqlite3, not ORM-managed) stores site metadata. Per-site databases (e.g., `instance/charlestonsc.db`) hold all ORM models.

**App factory:** `app/__init__.py` → `create_app()` initializes Flask, extensions, APScheduler (3AM daily pipeline), and registers blueprints.

**Blueprints:**
- `dashboard` (`/`) — buyer/owner/agent routes, admin user management, billing, agent listing creation, friend listing review
- `auth` (`/auth`) — registration, login, verification, password reset, masquerade, referral loop closure
- `social` (`/social`) — sharing, collections, reactions, referrals, points, leaderboard, friend listings ("Add a Home"), digest emails
- `site_manager` (`/admin/sites`) — master-only site CRUD
- `docs` (`/docs`) — documentation routes

**Background:**
- APScheduler runs pipeline at 3AM daily for all active sites
- `pipeline.py` is the CLI entry point for manual runs
- Pipeline includes two dedup layers: pre-upsert address normalization + post-upsert `deduplicate_existing()` cleanup

**Detail enrichment:** AJAX-based via `POST /listing/<id>/enrich` — detail page renders instantly; unenriched listings show a "Fetch Property Details" button instead of blocking on page load.

## Key Conventions

- **Use `site_url()` in templates**, not `url_for()` — preserves site context in multi-tenant URLs. Exceptions: `url_for('static', ...)` and `url_for('site_manager.*')`.
- **`g.site`** is always available in request context with registry data (site_key, db_path, map config, zip codes).
- **Relative imports** in route files: `from .. import db` to avoid circular imports with the factory pattern.
- **Guest support:** Flags/prefs/analyses stored in `session["guest_flags"]`, `session["guest_prefs"]`, `session["guest_analyses"]` — no login required.
- **User landmarks:** Up to 3 personal POI per user stored in `preferences_json` under `user_landmarks` key; managed via `POST /my-landmarks` (AJAX); appear in POI dropdown under "My Landmarks" optgroup.
- **Role-priority login:** When multiple accounts share the same email, login prefers the highest role (master > owner > agent > principal > client > user). Typing a specific username still logs in as that exact account.
- **Role switcher:** Master users see a "Switch Role" section in their username dropdown listing sibling accounts (same email) with role badges. One-click masquerade to any sibling; injected via `inject_siblings` context processor. Only visible to master and not during masquerade.
- **Masquerade:** Agents can impersonate own clients; master can impersonate anyone. Original user stored in `session['masquerade_original_id']`.
- **Chained masquerade:** Master can masquerade as agent, then agent can masquerade as principal (master -> agent -> principal). `masquerade_original_id` is set only on the first hop and never overwritten, so "End Preview" always returns straight to the true original user regardless of chain depth.
- **Never touch master accounts in migrations** — never write UPDATE/seed that sets a role on `role='master'` users. Only promote FROM `role='user'`.

## Core Modules

- **`app/models.py`** — ORM models: User, AgentProfile, Listing, DealScore, UserFlag, ListingNote, ApiCallLog, CachedAnalysis, AgentClientNote, OwnerAgentNote, PromptOverride, StreetWatch, StreetWatchAlert
- **`app/models_social.py`** — Social models: SocialShare, SocialReaction, SocialCollection, SocialCollectionItem, Referral, UserPoints, UserPointLog, FriendListing
- **`app/scraper/scorer.py`** — 18-factor deal score computation (includes proximity POI); dedup functions: `_normalize_address()`, `_merge_listing_data()`, `_deduplicate_listings()`, `deduplicate_existing()`
- **`app/services/deal_analyst.py`** — Claude AI integration for deal briefs, portfolio analysis, preference coaching
- **`app/services/registry.py`** — Registry.db CRUD (raw sqlite3, not ORM); includes `landmarks_json` per-site column for POI landmarks, `scheduler_locked` (master-only scheduler disable), `max_fetches_per_run` (pipeline listing cap)
- **`app/services/points.py`** — Points system: 7 earning actions, 50/day cap, leaderboard queries
- **`app/services/billing.py`** — Billing tiers (free/basic/pro/unlimited), usage quotas on AI and fetch calls, budget caps with email alerts at 80%/100%
- **`app/services/social_digest.py`** — Social digest email generation and sending
- **`app/scraper/zillow.py`** / **`realtor.py`** — RapidAPI scrapers
- **`config.py`** — Flask config, pipeline constants, DEFAULT_PREFS, DEFAULT_PROMPTS

## User Roles

`master` > `owner` > `agent` > `client`/`principal` > guest (no account)

- **Master:** Site registry management, masquerade as anyone, all capabilities; can add/remove zips from site via Preferences map (`canAddZips` flag); site creation seeds agent profiles + principal links
- **Owner:** Metrics, agent approval, site-wide prompts, manual pipeline trigger, user management (suspend/reactivate/delete via `/admin/users`), billing configuration (`/admin/billing`), target area labeling (assign zips from master's list but cannot add new zips)
- **Agent:** Client roster, branding, agent-specific prompts, masquerade as own clients, share on behalf of clients, direct listing creation (source="agent"), friend listing review/approve/reject workflow
- **Principal:** Agent-managed user (preferences read-only)
- **Guest:** Browse, flag (session-persisted), AI deal analysis, share via link — no login needed

## Social Features

- **Sharing:** Any user can share a listing or collection via email/link with a personal message
- **Reactions:** Recipients can react (love, interested, not_for_me, etc.)
- **Collections:** Curated groups of listings that can be shared
- **Referrals:** Track who brought new users; reward attribution chain; referral loop closed at registration
- **Points system:** 7 earning actions (share, react, collect, refer, etc.) with 50 points/day cap; `/social/points` and `/social/leaderboard` routes
- **Friend listings:** Users submit homes via "Add a Home" (`/social/add-home`); agents review/approve/reject (`/agent/friend-listing/<id>/review|approve|reject`); approved listings enter the main feed
- **Social proof:** Most-shared badges, share counts, reaction summaries, leaderboard
- **Social digest:** Periodic email summaries of social activity (`/social/send-digest`)
- **Agent analytics:** Agents see client social activity; owners see site-wide social metrics

## Billing

Four tiers: **free**, **basic**, **pro**, **unlimited**. Each tier defines usage quotas for AI analysis calls and listing fetch calls. Budget caps trigger email alerts at 80% and 100% thresholds. Owners manage billing at `/admin/billing`.

## Deployment (IIS)

- `web.config` configures HttpPlatformHandler → Waitress
- After `.py` changes: clear `__pycache__` dirs, then recycle IIS app pool
- Pipeline runs via APScheduler inside the app process (not a separate worker)
- Four test accounts per site using `philipalarson@gmail.com` (master, owner, agent, user roles)

## Testing

84 integration tests across 7 test files. Run with `pytest` from the project root.

## Docs

- `docs/master/AI_TUNE_SPEC.md` — AI Tune & Buyer Profile technical spec
- `docs/agent/AGENT_GUIDE.md` — agent role guide
- `docs/master/ARCHITECTURE.md` — system architecture overview
- `docs/master/DEPLOYMENT_GUIDE.md` — deployment instructions
- `docs/owner/OWNER_GUIDE.md` — owner role guide
- `docs/owner/ROLES_AND_PERMISSIONS.md` — role hierarchy and permissions
- `docs/SCORING_DEEP_DIVE.md` — 18-factor deal scoring details
- `docs/SOCIAL_CONCEPT.md` — social features concept/design
- `docs/master/SOCIAL_TECH_SPEC.md` — social features technical spec
- `docs/STREET_WATCH.md` — street watch feature docs
- `docs/master/TECHNICAL_REFERENCE.md` — developer technical reference
- `docs/master/TESTING.md` — test suite documentation
- `docs/USER_GUIDE.md` — end-user feature guide
