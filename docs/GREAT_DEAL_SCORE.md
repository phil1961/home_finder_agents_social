# Great Deal Score — Feature Documentation

Updated: 2026-03-18

---

## Overview

The Great Deal Score is a user-configurable threshold that visually highlights listings on the dashboard that exceed a minimum composite deal score. It provides instant visual feedback on which properties are standouts based on the user's personalized scoring weights.

## How It Works

Every listing receives a **composite deal score** (0–100) calculated from 18 weighted factors (price, size, yard, features, flood risk, year built, etc.). Each user's scoring importance weights determine how these factors combine into their personalized composite. The Great Deal Threshold defines the cutoff above which a listing is flagged as a "Great Deal."

### Threshold Setting

- **Location:** Preferences page → Display Settings → Great Deal Threshold slider
- **Range:** 0–100 (step: 1)
- **Default:** 75
- **Storage:** `preferences_json.great_deal_threshold` on the User model; `session["guest_prefs"]` for guests

### Visual Effects

When a listing's personalized composite score meets or exceeds the threshold:

**Dashboard listing cards:**
- 5px green left border
- Light green gradient background
- Subtle green box shadow
- **"Great Deal" badge** (green pill with trophy icon) displayed next to the address

**Dashboard banner (top of page):**
- **Great deals exist:** Bright green banner with trophy icon — "N Great Deals! N of X listings scored above your threshold of Y — top score: Z"
- **No great deals:** Subdued gray banner — "X listings scored — no listings above your Great Deal threshold of Y yet (top score: Z)"

### What It Does NOT Affect

- Does not change the composite score calculation
- Does not filter or hide any listings
- Does not affect AI analysis or deal briefs
- Does not change sort order
- Is purely a visual highlight and banner message

## Data Flow

```
User sets threshold on Preferences page
        ↓
Saved via AJAX POST to /preferences (scoring section)
        ↓
Stored in preferences_json.great_deal_threshold
        ↓
Dashboard route (listings.py) reads threshold from user prefs
        ↓
Counts listings with composite >= threshold → great_deal_count
        ↓
Passes great_deal_threshold + since_stats.great_deal_count to template
        ↓
Banner: shows green "Great Deals!" or gray "no great deals" based on count
Cards:  applies .great-deal CSS class when score >= threshold
Badge:  "Great Deal" badge shown via CSS (.great-deal .great-deal-badge)
```

## Guest Behavior

- Guests can adjust the threshold on the Preferences page
- Threshold is stored in `session["guest_prefs"]["great_deal_threshold"]`
- Session-only — lost when browser closes (guest save modal warns about this)
- Default is 75, same as authenticated users

## Files Involved

| File | Role |
|------|------|
| `app/templates/dashboard/_prefs_scoring.html` | Threshold slider UI (Display Settings section) |
| `app/routes/preferences_routes.py` | Saves threshold in scoring POST handler |
| `app/routes/listings.py` | Reads threshold, counts great deals, passes to template |
| `app/templates/dashboard/index.html` | Banner logic + `.great-deal` card class + badge |
| `config.py` | `GREAT_DEAL_SCORE_THRESHOLD` constant (default 75) |

## CSS Classes

```css
/* Card highlight */
.listing-card.great-deal {
    border-left: 5px solid #16a34a;
    background: linear-gradient(135deg, #f0fdf4 0%, #fff 40%);
    box-shadow: 0 2px 8px rgba(22,163,74,0.12);
}

/* Badge (hidden by default, shown when parent has .great-deal) */
.listing-card.great-deal .great-deal-badge {
    display: inline-block !important;
}
```

## Relationship to Composite Score

The composite score is computed per-user:

```
composite = Σ(sub_score × normalized_weight) / Σ(weights)
```

Where each of the 18 sub-scores is 0–100 and each weight is 0–10 (set by the user on the Preferences page). The Great Deal Threshold is simply a visual cutoff applied to this composite — it does not participate in the scoring math.

### Example

- User sets threshold to 55
- Listing A scores 58 → highlighted as Great Deal
- Listing B scores 52 → normal display
- Same listing can be a "Great Deal" for one user but not another, because their scoring weights differ
