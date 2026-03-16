# HomeFinder — Deal Scoring Deep Dive

**Version:** 2026.03.15
**Last Updated:** 2026-03-15

---

## How Deal Scoring Works

Every listing in HomeFinder receives a **composite deal score** from 0 to 100. This score is personalized — two users looking at the same house will see different scores based on their individual preferences.

---

## The Two-Layer System

### Layer 1: Sub-Scores (Objective)

Each listing is scored on 18 individual factors. Most sub-scores are **objective** — they're the same for every user because they're based on the property's actual attributes. The exception is **Proximity POI**, which is per-user (each user selects their own landmark).

### Layer 2: Composite Score (Personalized)

The composite score is a **weighted average** of the 18 sub-scores, using each user's importance weights (0–10 scale). This is where personalization happens.

```
composite = Σ (sub_score[i] × weight[i]) / Σ weight[i]
```

---

## Sub-Score Formulas

### Price Score

The price score uses a "sweet spot" model, not a simple cheaper-is-better approach.

```
sweet_spot = max_budget × 0.70
if price <= sweet_spot:
    score = 100
elif price <= max_budget:
    score = 100 - ((price - sweet_spot) / (max_budget - sweet_spot)) × 70
else:
    score = max(5, 30 - ((price - max_budget) / max_budget) × 100)
```

**Why 70%?** Homes priced well below budget often have issues. The sweet spot rewards properties that are affordable but not suspiciously cheap.

| Price vs Budget | Score |
|-----------------|-------|
| ≤ 70% of max | 100 |
| 85% of max | ~65 |
| At max | ~30 |
| 20% over max | ~10 |

### Size Score

```
if sqft >= 3000: score = 100
elif sqft >= 2500: score = 90
elif sqft >= 2000: score = 75
elif sqft >= 1500: score = 55
elif sqft >= 1200: score = 35
else: score = 5
```

### Yard Score

```
if lot_sqft >= 20000: score = 100
elif lot_sqft >= 15000: score = 90
elif lot_sqft >= 10000: score = 75
elif lot_sqft >= 7500: score = 55
elif lot_sqft >= 5000: score = 40
else: interpolated proportionally
```

### Feature Score

Up to 100 points from:
- **Garage:** +20 points
- **Porch:** +20 points
- **Patio:** +20 points
- **Bedrooms:** +5 per bedroom (max +20)
- **Bathrooms:** +5 per bathroom (max +15)

### Flood Score

| Condition | Score |
|-----------|-------|
| Above flood plain | 100 |
| Zone X (minimal risk) | 85 |
| Not in flood zone | 70 |
| In flood zone | 30 |
| Zone AE/VE (high risk) | 15 |

### Year Built Score

```
if year >= 2020: score = 100
elif year >= 2010: score = 90
elif year >= 2000: score = 75
elif year >= 1990: score = 60
elif year >= 1980: score = 45
elif year >= 1970: score = 35
elif year >= 1960: score = 30
else: interpolated down to ~15
```

### Single Story Score

| Stories | Score |
|---------|-------|
| 1 (confirmed) | 100 |
| Unknown | 50 |
| 2 | 40 |
| 3+ | 15 |

### Price Per Square Foot Score

Benchmarked against local market norms:

| $/sqft | Score |
|--------|-------|
| ≤ $120 | 100 |
| $150 | 85 |
| $175 | 70 |
| $200 | 50 |
| $225 | 35 |
| $250 | 20 |
| ≥ $275 | 5 |

### Days on Market Score

| Days | Score |
|------|-------|
| < 7 | 100 |
| 7–14 | 85 |
| 14–30 | 70 |
| 30–45 | 50 |
| 45–60 | 35 |
| > 60 | 20 |

### HOA Score

| Monthly HOA | Score |
|-------------|-------|
| None / $0 | 100 |
| $50 | 85 |
| $100 | 70 |
| $200 | 50 |
| $300 | 35 |
| $400 | 20 |
| ≥ $500 | 10 |

### Medical Proximity Score

| Distance to Hospital | Score |
|----------------------|-------|
| < 1 mile | 100 |
| 1–2 miles | 85 |
| 2–5 miles | 65 |
| 5–8 miles | 40 |
| 8–10 miles | 25 |
| > 10 miles | 10 |

### Grocery Proximity Score

| Distance to Grocery | Score |
|---------------------|-------|
| < 0.5 miles | 100 |
| 0.5–1 mile | 80 |
| 1–1.5 miles | 60 |
| 1.5–2 miles | 40 |
| > 2 miles | 20 |

### Community Pool Score

| Pool | Score |
|------|-------|
| Yes | 100 |
| No | 10 |

### Property Tax Score

```
tax_rate = annual_tax / price
if tax_rate < 0.005: score = 100
elif tax_rate < 0.01: score = 80
elif tax_rate < 0.015: score = 60
elif tax_rate < 0.02: score = 40
else: score = 20
```

### Lot Ratio Score

```
ratio = lot_sqft / sqft
if ratio >= 2.0: score = 100
elif ratio >= 1.5: score = 80
elif ratio >= 1.0: score = 60
elif ratio >= 0.75: score = 40
elif ratio >= 0.5: score = 25
else: score = 10
```

### Price Trend Score

| Trend | Score |
|-------|-------|
| Price dropped > 5% | 100 |
| Price dropped 1–5% | 85 |
| No change | 60 |
| Price increased 1–5% | 35 |
| Price increased > 5% | 20 |

### Walkability Score

Direct mapping: the walkability score (0–100) from external data is used as-is.

### Proximity POI Score (Per-User)

Unlike the other 17 factors, this score is **per-user** — each user selects their own landmark (point of interest) from the "Distance from..." dropdown. Landmarks come from two sources:

1. **Site-wide landmarks** — managed by owners/masters via the Landmarks panel on the Preferences page (stored in `registry.db` `landmarks_json`)
2. **Personal landmarks ("My Landmarks")** — up to 3 per user, added via the "My Landmarks" section on the Preferences page (stored in `preferences_json` under `user_landmarks`)

Both types appear in the dropdown, with personal landmarks grouped under a "My Landmarks" optgroup. The score uses the Haversine formula to calculate straight-line distance from the listing to the selected landmark.

| Distance to Landmark | Score |
|----------------------|-------|
| 0–1 miles | 100 |
| 1–5 miles | 100–70 (linear interpolation) |
| 5–10 miles | 70–30 (linear interpolation) |
| 10–15 miles | 30–0 (linear interpolation) |
| 15+ miles | 0 |

**Activation:** Users select a landmark on the Preferences page ("Distance from..." dropdown in the Location & Lifestyle section). Setting `imp_proximity_poi` to 0 (the default) disables this factor entirely — it contributes nothing to the composite score.

**Without user context:** During pipeline scoring (no user), the POI score defaults to a neutral 50.

**User preferences keys:** `proximity_poi_name`, `proximity_poi_lat`, `proximity_poi_lng`, `imp_proximity_poi`

**Implementation:** `score_proximity_poi()` and `_haversine_miles()` in `app/scraper/scorer.py`

---

## Default Importance Weights

New users start with these weights (0–10 scale):

| Factor | Default Weight |
|--------|---------------|
| price | 8 |
| features | 8 |
| yard | 7 |
| single_story | 7 |
| flood | 6 |
| hoa | 6 |
| community_pool | 6 |
| year_built | 5 |
| size | 5 |
| proximity_medical | 5 |
| proximity_grocery | 5 |
| price_per_sqft | 4 |
| property_tax | 4 |
| price_trend | 4 |
| days_on_market | 3 |
| lot_ratio | 3 |
| walkability | 3 |
| proximity_poi | 0 (off by default) |

---

## Great Deal Threshold

Listings scoring **75 or above** are flagged as "great deals" in the UI with a green badge. This threshold is configurable in `config.py` (`GREAT_DEAL_SCORE_THRESHOLD`).

---

## Per-User Recalculation

Composite scores are recalculated **on-demand** when a user views listings. The flow:

1. User loads dashboard or listing detail
2. System fetches the listing's 18 sub-scores from `DealScore` (POI score is recomputed per-user)
3. Calls `compute_user_composite(user_prefs)` with the user's weights and price range
4. Returns the personalized composite — displayed but **not stored** (it's always fresh)

This means changing your preferences instantly changes all your scores without any background processing.

---

## Missing Data Handling

When data is missing for a factor:
- **Sub-score defaults to 50** (neutral) for most factors
- **Price per sqft:** Requires both price and sqft; 50 if either missing
- **Flood:** 70 (benefit of the doubt) if no flood data
- **Single story:** 50 (unknown) if stories field is NULL
- **Community pool:** 10 (assume no) if not specified

- **Proximity POI:** 50 (neutral) if no landmark selected or listing lacks coordinates

This ensures listings with incomplete data aren't unfairly penalized or rewarded.
