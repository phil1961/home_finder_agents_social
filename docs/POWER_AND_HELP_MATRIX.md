<!--
  File: docs/POWER_AND_HELP_MATRIX.md
  App Version: 2026.03.17 | File Version: 1.0.0
  Last Modified: 2026-03-17
-->

# Power Mode & Help Level Matrix

Quick reference for how Power Mode, Help Level, and tooltips interact across the UI.

---

## Power Mode (UI Complexity)

Controls which nav icons and scoring sliders are visible. Hidden sliders keep their values via hidden inputs — scoring is never affected, only the UI.

| | Low | Mid | High |
|---|---|---|---|
| **Default for** | Guests | — | Registered users |
| **Nav icons** | Dashboard, Map, Favorites, Preferences, Help | + Digest, Watch, Social, Feedback | + Tour, Contact Agent |
| **Scoring sliders** | 6 | 12 | 18 |
| **Target Areas map** | Hidden | Hidden | Owner/Master only |

### Sliders by Power Level

| Power | Category | Sliders |
|-------|----------|---------|
| **Low** | Core Factors | Price, Size, Yard, Features, Flood, Year Built |
| **Mid** | + Property & Deal | Single Story, Price/SqFt, Days on Market, HOA, Property Tax, Price Trend |
| **High** | + Location & Lifestyle | Near Landmark, Near Medical, Near Grocery, Community Pool, Lot Ratio, Walkability |

---

## Help Level (Contextual Guidance)

Controls tooltips and inline help text throughout the site.

| | Level 1 (Expert) | Level 2 (Standard) | Level 3 (Guided) |
|---|---|---|---|
| **Default for** | — | Registered users | Guests |
| **Tooltips on hover** | No | Yes | Yes |
| **Inline help text** | No | No | Yes |
| **Listing card tooltip** | No | "Click anywhere..." | "Click anywhere..." |
| **Deal Score hint** | No | Tooltip only | Tooltip + inline explanation |
| **Price Range hint** | No | Tooltip only | Tooltip + inline explanation |

---

## Tooltip Coverage (Level 2+)

| Location | Elements |
|----------|----------|
| **Navbar** | Dashboard, Map, Digest, Favorites, Watch, Tour, Preferences, Feedback |
| **Dashboard filters** | Area, Sort, Flag, Source, Min Score |
| **Listing cards** | Deal score ring, entire card ("Click anywhere on this card to see full details") |
| **Detail page** | Deal Score card, AI "Analyze This Deal" button, "Fetch Property Details" button |
| **Preferences** | Price Range header, Great Deal Threshold label, Near Landmark label |

---

## Typical User Profiles

| | Guest (new) | Registered (default) | Power user |
|---|---|---|---|
| **Power Mode** | Low | High | High |
| **Help Level** | 3 (Guided) | 2 (Standard) | 1 (Expert) |
| **Sees** | 5 nav icons, 6 sliders, tooltips + inline help | All nav, all sliders, tooltips only | All nav, all sliders, no hints |

---

## Toggle Locations

Both settings save instantly on click via AJAX — no save button needed.

| Setting | Help Dropdown | Preferences Page | AJAX Route |
|---------|--------------|-----------------|------------|
| Help Level | 1 / 2 / 3 buttons | Radio cards at top | `POST /api/help-level` |
| Power Mode | Low / Mid / High buttons | Button group at top | `POST /api/power-mode` |

---

## Implementation Details

- **Preferences storage:** Both stored in `preferences_json` as `help_level` (int 1-3) and `power_mode` (string "low"/"mid"/"high")
- **Guest storage:** `session["guest_prefs"]` — same keys
- **Context processor:** `inject_help_and_power()` in `app/__init__.py` injects both into all templates
- **JS module:** `app/static/js/help-hints.js` reads `window.HF_HELP_LEVEL` and activates Bootstrap tooltips on `[data-help]` elements, shows/hides `.help-hint` blocks
- **Template pattern for tooltips:** Add `data-help="tooltip text"` to any HTML element
- **Template pattern for inline hints:** Add `<div class="help-hint d-none">...</div>` — shown at level 3
- **Template pattern for power gating:** `{% if pm in ('mid', 'high') %}...{% endif %}` or `{% if power_mode|default('high') != 'low' %}`
