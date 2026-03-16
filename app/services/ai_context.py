# v20260310-1
"""
AI Context Builders — pure string-building functions for Claude prompts.

These functions construct the textual context sent to Claude for deal analysis,
portfolio analysis, and preference coaching. They contain no I/O, no API calls,
and are easily unit-testable.
"""


def _get_site_display_name() -> str:
    """Return the current site's display_name, or a generic fallback."""
    try:
        from flask import g
        return getattr(g, "site", {}).get("display_name", "the local area")
    except RuntimeError:
        return "the local area"


def build_listing_context(listing, deal_score=None, user_prefs=None) -> str:
    """Build a rich context string about a listing for Claude to analyze."""

    # Basic info
    lines = [
        f"Property: {listing.address}",
        f"Price: ${listing.price:,}",
        f"Beds: {listing.beds}  |  Baths: {listing.baths}  |  Sqft: {listing.sqft:,}",
    ]

    if listing.lot_sqft:
        lines.append(f"Lot size: {listing.lot_sqft:,} sqft ({listing.lot_sqft / 43560:.2f} acres)")
    if listing.year_built:
        lines.append(f"Year built: {listing.year_built}")
    if listing.price_per_sqft:
        lines.append(f"Price per sqft: ${listing.price_per_sqft:,.0f}")

    # Extended data
    if listing.days_on_market:
        lines.append(f"Days on market: {listing.days_on_market}")
    if listing.hoa_monthly is not None:
        lines.append(f"HOA: ${listing.hoa_monthly:,.0f}/month" if listing.hoa_monthly > 0 else "HOA: None")
    if listing.property_tax_annual:
        lines.append(f"Estimated annual property tax: ${listing.property_tax_annual:,.0f}")
    if listing.is_single_story is not None:
        lines.append(f"Single story: {'Yes' if listing.is_single_story else 'No'}")
    if listing.stories:
        lines.append(f"Stories: {listing.stories}")
    if listing.price_change_pct is not None:
        direction = "dropped" if listing.price_change_pct < 0 else "increased"
        lines.append(f"Price has {direction} {abs(listing.price_change_pct):.1f}%")
    if listing.has_community_pool:
        lines.append("Community pool: Yes")

    # Features
    features = []
    if listing.has_garage:
        features.append("garage")
    if listing.has_porch:
        features.append("porch")
    if listing.has_patio:
        features.append("patio")
    if listing.above_flood_plain:
        features.append("above flood plain")
    if listing.flood_zone:
        features.append(f"FEMA zone: {listing.flood_zone}")
    if features:
        lines.append(f"Features: {', '.join(features)}")

    # Source + URL
    lines.append(f"Source: {listing.source.capitalize()}")
    if listing.url:
        lines.append(f"Listing URL: {listing.url}")

    # Description (truncated)
    if listing.description:
        desc = listing.description[:1500]
        lines.append(f"\nListing description:\n{desc}")

    # Deal score breakdown
    if deal_score:
        lines.append(f"\n--- Deal Score: {deal_score.composite_score:.0f}/100 ---")
        lines.append(f"Price score: {deal_score.price_score:.0f}/100")
        lines.append(f"Size score: {deal_score.size_score:.0f}/100")
        lines.append(f"Yard score: {deal_score.yard_score:.0f}/100")
        lines.append(f"Feature score: {deal_score.feature_score:.0f}/100")
        lines.append(f"Flood score: {deal_score.flood_score:.0f}/100")
        ext = deal_score.extended_scores or {}
        for key, label in [
            ("year_built_score", "Year Built"),
            ("single_story_score", "Single Story"),
            ("price_per_sqft_score", "Price/Sqft"),
            ("days_on_market_score", "Days on Market"),
            ("hoa_score", "HOA"),
            ("property_tax_score", "Property Tax"),
            ("price_trend_score", "Price Trend"),
        ]:
            val = ext.get(key)
            if val is not None:
                lines.append(f"{label} score: {val:.0f}/100")

    # Buyer preferences context
    if user_prefs:
        lines.append(f"\n--- Buyer Criteria ---")
        lines.append(f"Budget: ${user_prefs.get('min_price', 200000):,} – ${user_prefs.get('max_price', 600000):,}")
        lines.append(f"Min beds: {user_prefs.get('min_beds', 4)}, Min baths: {user_prefs.get('min_baths', 3)}")
        must_haves = []
        if user_prefs.get("must_have_garage"):
            must_haves.append("garage")
        if user_prefs.get("must_have_porch"):
            must_haves.append("porch")
        if user_prefs.get("must_have_patio"):
            must_haves.append("patio")
        if must_haves:
            lines.append(f"Must-haves: {', '.join(must_haves)}")
        lines.append(f"Location: {_get_site_display_name()} (retirement home)")
        lines.append("Buyer is retired, prioritizes single-story living, "
                     "large yard, proximity to family, above flood plain")

    return "\n".join(lines)


def build_compact_listing(listing, user_composite: float) -> str:
    """Build a compact one-block summary of a listing for portfolio context."""
    lines = [f"#{listing.id}: {listing.address}"]
    lines.append(f"  ${listing.price:,}  |  {listing.beds}BR/{listing.baths}BA  |  {listing.sqft:,} sqft")
    if listing.lot_sqft:
        lines.append(f"  Lot: {listing.lot_sqft:,} sqft ({listing.lot_sqft / 43560:.2f} acres)")
    if listing.year_built:
        lines.append(f"  Built: {listing.year_built}")
    if listing.days_on_market:
        lines.append(f"  Days on market: {listing.days_on_market}")
    if listing.hoa_monthly is not None:
        lines.append(f"  HOA: ${listing.hoa_monthly:,.0f}/mo" if listing.hoa_monthly else "  HOA: None")

    features = []
    if listing.has_garage: features.append("garage")
    if listing.has_porch: features.append("porch")
    if listing.has_patio: features.append("patio")
    if listing.above_flood_plain: features.append("above flood plain")
    if listing.flood_zone: features.append(f"FEMA {listing.flood_zone}")
    if listing.is_single_story: features.append("single story")
    if listing.has_community_pool: features.append("community pool")
    if features:
        lines.append(f"  Features: {', '.join(features)}")

    if listing.has_price_changes:
        history = listing.price_history
        first_price = history[0]["price"]
        drop = first_price - listing.price
        if drop > 0:
            lines.append(f"  Price dropped ${drop:,} from original ${first_price:,}")
        elif drop < 0:
            lines.append(f"  Price increased ${abs(drop):,} from original ${first_price:,}")

    if listing.price_per_sqft:
        lines.append(f"  $/sqft: ${listing.price_per_sqft:,.0f}")

    lines.append(f"  Deal Score: {user_composite:.0f}/100")
    return "\n".join(lines)


def build_portfolio_context(listings, user_composites: dict, user_prefs: dict,
                            flag_label: str = "selected") -> tuple:
    """
    Build context strings for portfolio analysis.

    Returns:
        (system_context, user_message) — the system context suffix and user message
        to be combined with the system prompt by the caller.

    system_context contains the buyer profile lines to append to the system prompt.
    user_message contains the formatted listing blocks.
    """
    # Build compact context for all listings
    listing_blocks = []
    for listing in listings:
        composite = user_composites.get(listing.id, 0)
        listing_blocks.append(build_compact_listing(listing, composite))

    all_listings_text = "\n\n".join(listing_blocks)

    # Buyer context
    budget_min = user_prefs.get("min_price", 200000)
    budget_max = user_prefs.get("max_price", 600000)
    min_beds = user_prefs.get("min_beds", 4)
    min_baths = user_prefs.get("min_baths", 3)

    must_haves = []
    if user_prefs.get("must_have_garage"): must_haves.append("garage")
    if user_prefs.get("must_have_porch"): must_haves.append("porch")
    if user_prefs.get("must_have_patio"): must_haves.append("patio")

    system_context = (
        f"You've been given the buyer's \"{flag_label}\" list — "
        f"the {len(listings)} properties they're most interested in.\n\n"
        "{{BASE_PROMPT}}"
        f"\n\nBuyer profile:\n"
        f"- Budget: ${budget_min:,} – ${budget_max:,}\n"
        f"- Min {min_beds}BR / {min_baths}BA\n"
        f"- Retired couple, wants: single story, large yard, above flood plain, near family\n"
        + (f"- Must-haves: {', '.join(must_haves)}\n" if must_haves else "")
        + f"- Location: {_get_site_display_name()}"
    )

    user_message = (
        f"Here are my {len(listings)} {flag_label.lower()} properties. "
        f"Give me the big picture.\n\n"
        f"{all_listings_text}"
    )

    return system_context, user_message


def build_preferences_context(prefs: dict, defaults: dict) -> str:
    """
    Build a readable context string summarizing a user's scoring preferences.

    Returns a formatted string suitable as the user message content for
    preferences analysis.
    """
    imp_labels = {
        "imp_price": "Price",
        "imp_size": "House Size",
        "imp_yard": "Yard Size",
        "imp_features": "Features (garage, porch, patio, beds, baths)",
        "imp_flood": "Flood Risk",
        "imp_year_built": "Year Built",
        "imp_single_story": "Single Story",
        "imp_price_per_sqft": "Price per Sqft",
        "imp_days_on_market": "Days on Market",
        "imp_hoa": "HOA Fee",
        "imp_proximity_medical": "Near Medical",
        "imp_proximity_grocery": "Near Grocery",
        "imp_community_pool": "Community Pool",
        "imp_property_tax": "Property Tax",
        "imp_lot_ratio": "Lot-to-House Ratio",
        "imp_price_trend": "Price Trend",
        "imp_walkability": "Walkability",
    }

    weight_lines = []
    turned_off = []
    high_priority = []
    for key, label in imp_labels.items():
        val = prefs.get(key, defaults.get(key, 5))
        default_val = defaults.get(key, 5)
        diff = ""
        if val != default_val:
            diff = f" (default: {default_val})"
        weight_lines.append(f"  {label}: {val}/10{diff}")
        if val == 0:
            turned_off.append(label)
        elif val >= 8:
            high_priority.append(label)

    weights_text = "\n".join(weight_lines)

    # Must-haves
    must_haves = []
    if prefs.get("must_have_garage"):
        must_haves.append("garage")
    if prefs.get("must_have_porch"):
        must_haves.append("porch")
    if prefs.get("must_have_patio"):
        must_haves.append("patio")

    context = f"""BUYER PREFERENCES CONFIGURATION:

Budget: ${prefs.get('min_price', 200000):,} – ${prefs.get('max_price', 600000):,}
Min Bedrooms: {prefs.get('min_beds', 4)}
Min Bathrooms: {prefs.get('min_baths', 3)}
Must-haves: {', '.join(must_haves) if must_haves else 'None specified'}

SCORING WEIGHTS (0 = off, 10 = critical):
{weights_text}

Factors turned OFF (0): {', '.join(turned_off) if turned_off else 'None'}
Highest priority (8-10): {', '.join(high_priority) if high_priority else 'None'}

CONTEXT:
- Buyer is a retired couple
- Location: {_get_site_display_name()}
- Priorities: single-story, large yard, above flood plain, near family
- This is a 17-factor scoring system — each listing gets scored 0-100 on every factor,
  then these weights determine how much each factor contributes to the final composite score"""

    return context
