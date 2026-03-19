# AI Tune & Buyer Profile — Technical Specification

**Version:** 2026.03.18
**Last Updated:** 2026-03-18

---

## Overview

The AI Tune feature personalizes Claude AI analysis by injecting a buyer demographic profile into the prompt context. Instead of generic deal analysis, Claude tailors its commentary to the buyer's life stage, interests, mobility needs, community preferences, and relocation context.

### Three AI Modes

| Mode | Behavior |
|------|----------|
| **Off** | All AI panels hidden (Deal Analyst, Portfolio Analyst, Preferences Coach) |
| **On** | Standard analysis with generic buyer line: "Buyer is searching for a home in the area" |
| **Tune** | Personalized analysis — full buyer profile block appended to every AI context |

- Available to **authenticated users** only; guests default to AI Off.
- Mode selection persists in `preferences_json.ai_mode` (users) or `session["guest_prefs"]["ai_mode"]` (guests).

---

## Architecture

### Settings Flow

1. Settings page (`/settings`) contains an **AI Analysis** card with Off / On / Tune tiles.
2. Selecting **Tune** reveals the buyer profile questionnaire inline (no page reload).
3. All saves via AJAX — mode changes hit `/api/ai-mode`, profile saves hit `/api/buyer-profile`.

### Data Flow

```
User fills questionnaire → AJAX POST /api/buyer-profile → stored in preferences_json.buyer_profile
                                                              ↓
User clicks "Analyze" → ai_routes.py loads user prefs → ai_context.py builds context
                                                              ↓
                                                    build_buyer_profile_context() converts
                                                    profile dict → natural language block
                                                              ↓
                                                    Appended to listing/portfolio/prefs context
                                                              ↓
                                                    Sent to Claude API via deal_analyst.py
```

### Storage

- Buyer profile stored as `buyer_profile` dict inside `preferences_json` on the `User` model.
- Guest profiles stored in `session["guest_prefs"]["buyer_profile"]`.
- Profile preserved across scoring saves (explicit preservation in preferences POST handler).

---

## Buyer Profile Schema

| Field | Type | Values | Description |
|-------|------|--------|-------------|
| `life_stage` | string | `young_professional` \| `growing_family` \| `established_family` \| `empty_nester` \| `pre_retirement` \| `retired` | Primary demographic segment |
| `kids` | string \| null | `young` \| `school_age` \| `teens` | Age range of children (nullable) |
| `pets` | string \| null | `dog` \| `cat` \| `both` | Pet ownership (nullable) |
| `work_from_home` | string \| null | `full` \| `hybrid` \| `no` | Remote work situation (nullable) |
| `partner` | boolean | — | Moving with spouse/partner |
| `budget_feel` | string | `stretching` \| `comfortable` \| `flexible` | Subjective budget comfort level |
| `fixed_income` | boolean | — | On fixed income |
| `activities` | list[string] | `golf` \| `fishing` \| `beach` \| `running` \| `gardening` \| `hunting` \| `dining` \| `arts` \| `fitness` \| `swimming` | Lifestyle interests (multi-select) |
| `worship_important` | boolean | — | Proximity to church matters |
| `denomination` | string | Free text | Preferred denomination (optional) |
| `community_style` | string | `quiet` \| `friendly` \| `active` | Neighborhood vibe preference |
| `school_quality` | boolean | — | School quality matters (conditional on `kids`) |
| `school_district` | string | Free text | Preferred school district (optional) |
| `single_story_important` | boolean | — | Single-story preference |
| `medical_proximity` | boolean | — | Proximity to medical facilities matters |
| `walkability_important` | boolean | — | Walkability preference |
| `relocating_from` | string | Free text | City/state/region the buyer is moving from |

---

## API Endpoints

### POST `/api/ai-mode`

Sets the AI analysis mode for the current user or guest session.

**Request body:**
```json
{"mode": "off"|"on"|"tune"}
```

**Response:**
```json
{"ok": true, "ai_mode": "tune"}
```

- Works for both guests and authenticated users.
- Guests: stored in `session["guest_prefs"]["ai_mode"]`.
- Users: stored in `preferences_json.ai_mode`.

### POST `/api/buyer-profile`

Saves the buyer profile questionnaire answers.

**Request body:**
```json
{
  "profile": {
    "life_stage": "retired",
    "partner": true,
    "activities": ["golf", "fishing"],
    "medical_proximity": true,
    "relocating_from": "Chicago, IL"
  }
}
```

**Response:**
```json
{"ok": true}
```

- Server-side whitelist validation of allowed keys — unknown keys are silently dropped.
- Works for both guests and authenticated users.

---

## Context Integration

### `build_buyer_profile_context(buyer_profile: dict) → str`

Converts a profile dict into a natural language `--- Buyer Profile ---` block suitable for Claude prompt injection.

- Returns **empty string** if profile is empty or `None`.
- Called by all three context builders:
  - `build_listing_context()` — Deal Analyst
  - `build_portfolio_context()` — Portfolio Analyst
  - `build_preferences_context()` — Preferences Coach

**Example output:**
```
--- Buyer Profile ---
Life stage: Retired
Moving with partner: Yes
On fixed income: Yes
Activities/interests: golf, fishing
Proximity to medical facilities: Important
Relocating from: Chicago, IL
Community preference: quiet
Single-story preference: Yes
---
```

### `_buyer_summary_line(buyer_profile: dict) → str`

Generates a one-line summary for the system prompt.

- **With profile:** `"Retiree, with partner, interests: golf, fishing"`
- **Without profile:** `"Buyer is searching for a home in the area"`

### Without Profile (ai_mode = "on")

- Generic buyer line injected: `"Buyer is searching for a home in the area"`
- No `--- Buyer Profile ---` block appended.
- Claude gives standard, non-personalized analysis.

### With Profile (ai_mode = "tune")

- Full buyer profile block appended to context.
- Claude tailors analysis to life stage, activities, community preferences, health needs.
- Example output differences:
  - Mentions proximity to golf courses for golfers
  - References church denominations and nearby congregations
  - Highlights school districts when kids are present
  - Compares climate/cost-of-living when `relocating_from` is set

---

## Template Integration

### Settings Page (`settings.html`)

- **AI Analysis card** with Off / On / Tune tile selectors.
- Selecting Tune reveals the questionnaire panel with **8 sections**:
  1. Life Stage
  2. Household (partner, kids, pets)
  3. Work Situation
  4. Budget & Income
  5. Activities & Interests
  6. Community & Faith
  7. Schools (conditional on kids selection)
  8. Mobility & Health
  9. Relocating From
- **Chip-based UI** for single-select and multi-select fields.
- **Toggle pills** for boolean fields.
- **Auto-save** via AJAX on "Save Profile" button click.

### AI Visibility Guards

AI panels are wrapped in `ai_mode` conditionals across all dashboard templates:

| Template | Panel | Guard |
|----------|-------|-------|
| `detail.html` | Deal Analyst card | `{% if ai_mode\|default('on') != 'off' %}` |
| `index.html` | Portfolio Analyst card | `{% if ai_mode\|default('on') != 'off' %}` |
| `_prefs_ai_coach.html` | Preferences Coach card | `{% if ai_mode\|default('on') != 'off' %}` |

- Guest default: `ai_mode='off'` — AI panels hidden for unauthenticated users.

### Prompt Test Modal (`_prompt_preview_modal.html`)

- **"Include Bio" toggle** adds buyer profile to sample test data.
- Draggable modal (mousedown on header).
- Bio chips use the same styling as the Settings page questionnaire.
- Profile context appended via `_buildBioContext()` JS function in `_prompt_preview_js.html`.

---

## Files Changed

| File | Changes |
|------|---------|
| `app/__init__.py` | Context processor: inject `ai_mode` into all templates |
| `app/routes/preferences_routes.py` | `/settings` route, `/api/ai-mode`, `/api/buyer-profile` endpoints |
| `app/routes/ai_routes.py` | `buyer_profile` injected into preferences analysis prefs dict |
| `app/services/ai_context.py` | `build_buyer_profile_context()`, `_buyer_summary_line()`, dynamic profile in all 3 context builders |
| `app/services/deal_analyst.py` | Removed hardcoded "retired buyer" text |
| `app/templates/dashboard/settings.html` | AI Analysis card + Tune questionnaire UI |
| `app/templates/dashboard/detail.html` | `ai_mode` guard on Deal Analyst |
| `app/templates/dashboard/index.html` | `ai_mode` guard on Portfolio Analyst |
| `app/templates/dashboard/_prefs_ai_coach.html` | `ai_mode` guard on Preferences Coach |
| `app/templates/dashboard/_prompt_preview_modal.html` | Draggable modal, buyer profile section |
| `app/templates/dashboard/_prompt_preview_js.html` | `_buildBioContext()`, bio chip interactions |
| `app/templates/dashboard/admin_prompts.html` | Textarea styling upgrade |
| `app/templates/dashboard/agent_prompts.html` | Textarea styling upgrade |
| `app/templates/base.html` | Settings nav icon added |
