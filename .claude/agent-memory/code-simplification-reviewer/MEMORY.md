# HomeFinder Code Review Memory

## Key Files Reviewed (2026-03-10)
- `app/__init__.py` — app factory, SitePathMiddleware, _SiteRoutedSession, 6x separate migration functions
- `app/models.py` — 11 ORM models; User.DEFAULT_PREFS duplicates scorer.DEFAULT_IMPORTANCE
- `app/routes/dashboard.py` — 1677 lines, 30+ routes in a single file
- `app/routes/auth.py` — 505 lines, clean; _site_redirect defined here but imported by dashboard
- `app/routes/site_manager.py` — 399 lines, _init_site_db duplicates migration DDL from __init__.py
- `app/scraper/scorer.py` — 17 scoring functions + compute_deal_score; score_to_imp dict duplicated in models.py
- `app/services/deal_analyst.py` — 3 functions each calling Anthropic API with nearly identical HTTP boilerplate
- `pipeline.py` — run_pipeline, _upsert_listing, _score_listing, rescore_all_listings

## Critical Patterns & Issues

### dashboard.py Route Groupings (decomposition candidates)
- Lines 49-415: Public listing routes (welcome, index, detail, toggle_flag, map_view, digest)
- Lines 453-728: Preferences + API endpoints (preferences, api_places, api_toggle_flag)
- Lines 769-955: Admin routes (fetch_now, admin_metrics, admin_agents, admin_agent_action)
- Lines 958-1128: AI analysis routes (analyze_listing, analyze_portfolio, analyze_preferences)
- Lines 1130-1152: Help/why pages
- Lines 1154-1543: Agent routes (agent_dashboard, agent_client_notes, admin_agent_notes, admin_prompts, agent_prompts, agent_branding, agent_create_client, agent_client_prefs)
- Lines 1545-1677: Itinerary + contact routes (save_note, itinerary, contact_agent)

### Most Repeated Pattern: target_areas_json extraction
Appears 5x in dashboard.py (lines ~23, 126-132, 442-446, 489-499, 679-690).
Should be a helper: `get_site_target_areas(site) -> dict`

### Prefs form parsing duplicated
The block that reads min_price/max_price/min_beds/min_baths/must_have_*/imp_* from request.form
appears identically in `preferences()` (line 601-626) and `agent_client_prefs()` (line 1508-1525)
and `analyze_preferences()` (line 1093-1104). Should be `_parse_prefs_form() -> dict`.

### Migration system is fragmented
`__init__.py` has `_run_migrations()` plus 6 `_ensure_*_table()` functions.
`site_manager.py` has `_init_site_db()` that independently duplicates column DDL.
All of these should consolidate into a single migration module.

### Anthropic API call pattern duplicated 3x
`analyze_listing`, `analyze_portfolio`, `analyze_preferences` in deal_analyst.py all:
1. Build headers, POST to same URL, check status
2. Extract text from content blocks
3. Strip markdown fences
4. Parse JSON
5. Handle the same 3 exception types
Should extract `_call_anthropic(system, user_message, max_tokens, timeout) -> dict`

### Warning-level logging used for info
`app/__init__.py` and `models.py` use `log.warning()` and `app.logger.warning()` for normal
operational info (engine selection, session creation). This pollutes logs and makes real
warnings hard to find. Should be `log.debug()` or `log.info()`.

### Inline _GuestFlag class
`listing_detail()` (dashboard.py line ~271) defines an inline class `_GuestFlag` to mimic
UserFlag for guests. Should be a module-level namedtuple or dataclass.

### Hardcoded Charleston references
- `deal_analyst.py` lines 129, 131, 135 hardcode "Charleston, SC area" in AI prompts
- `scorer.py` line 135 comments "Charleston area ~$150-250/sqft" and that benchmark is baked in
- `config.py` DEFAULT_PROMPTS["preferences"] line 59 references "Charleston, SC market"
  These should come from the site registry's display_name / region fields.

### score_to_imp duplicated
`DealScore.SCORE_TO_IMP` (models.py lines 462-474) and local `score_to_imp` dict in
`compute_deal_score` (scorer.py lines 386-397) are identical. Should live in scorer.py only
and be imported by models.py.

### _site_redirect defined in auth.py but imported by dashboard.py
Better to move to a shared `app/utils.py` so neither blueprint imports from the other.

### contact_agent email HTML is inline
dashboard.py lines 1657-1667 build HTML directly in Python. Should use a template.

### agent_create_client has hardcoded email guard
Line 1425: `if client_email == "philipalarson@gmail.com":` — developer email hardcoded in production route.

### Missing db.session.add() before _ensure_* tables commit
All 6 _ensure_* functions call conn.commit() but not inside a transaction begin — fine for
sqlite3 direct calls but the pattern is inconsistent with ORM usage elsewhere.

## Architecture Decisions to Preserve
- site_url() in templates, NOT url_for() (except static/site_manager)
- Relative imports in route files: `from .. import db`
- g.site always available in request context
- Guest support: session["guest_flags"], session["guest_prefs"], session["guest_analyses"]
- _SiteRoutedSession proxy — replaces db.session at app init time
- SitePathMiddleware strips /site/<key> from PATH_INFO before Flask router sees it
- Never modify master-role users in migrations
