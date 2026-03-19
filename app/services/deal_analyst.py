# ─────────────────────────────────────────────
# File: app/services/deal_analyst.py
# App Version: 2026.03.14 | File Version: 1.5.0
# Last Modified: 2026-03-18
# ─────────────────────────────────────────────
"""
AI Deal Analyst — powered by Claude.

Generates buyer-focused deal briefs for any listing:
  - What's good about this property
  - What to watch out for
  - Negotiation leverage + suggested opening offer

This is the core competitive advantage: Zillow/Realtor serve sellers too,
so they'll never give adversarial buyer advice. We only serve the buyer.
"""
import json
import logging
import os
import time

import requests

from app.services.ai_context import (
    build_listing_context,
    build_portfolio_context,
    build_preferences_context,
)

log = logging.getLogger(__name__)

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_MODEL = "claude-sonnet-4-20250514"


def _get_api_key() -> str:
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY not set. Add it to your .env file. "
            "Get one at: https://console.anthropic.com/settings/keys"
        )
    return key


def _call_anthropic(system_prompt: str, user_message: str,
                    max_tokens: int = 1024, timeout: int = 30) -> dict:
    """POST to Anthropic API, extract text, parse JSON.
    Returns parsed dict on success or {"error": "..."} on failure."""
    api_key = _get_api_key()
    t0 = time.time()
    try:
        resp = requests.post(
            ANTHROPIC_API_URL,
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            json={
                "model": ANTHROPIC_MODEL,
                "max_tokens": max_tokens,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_message}],
            },
            timeout=timeout,
        )
        elapsed_ms = int((time.time() - t0) * 1000)

        if resp.status_code != 200:
            log.error(f"Anthropic API error {resp.status_code}: {resp.text[:300]}")
            result = {"error": f"API returned {resp.status_code}. Check your ANTHROPIC_API_KEY."}
            result["_meta"] = {"response_time_ms": elapsed_ms, "http_status": resp.status_code}
            return result

        data = resp.json()
        text = ""
        for block in data.get("content", []):
            if block.get("type") == "text":
                text += block.get("text", "")

        # Extract token usage if available
        usage = data.get("usage", {})
        input_tokens = usage.get("input_tokens")
        output_tokens = usage.get("output_tokens")

        # Strip markdown fences and parse JSON
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

        parsed = json.loads(text)
        parsed["_meta"] = {
            "response_time_ms": elapsed_ms,
            "http_status": resp.status_code,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        }
        return parsed

    except json.JSONDecodeError as e:
        elapsed_ms = int((time.time() - t0) * 1000)
        log.error(f"Failed to parse Claude response as JSON: {e}\nRaw: {text[:500]}")
        result = {"error": "AI returned an unexpected format. Please try again."}
        result["_meta"] = {"response_time_ms": elapsed_ms, "http_status": getattr(resp, 'status_code', None)}
        return result
    except requests.exceptions.Timeout:
        elapsed_ms = int((time.time() - t0) * 1000)
        result = {"error": f"AI analysis timed out ({timeout}s). Please try again."}
        result["_meta"] = {"response_time_ms": elapsed_ms, "http_status": None}
        return result
    except Exception as e:
        elapsed_ms = int((time.time() - t0) * 1000)
        log.error(f"Deal analyst error: {e}")
        result = {"error": str(e)}
        result["_meta"] = {"response_time_ms": elapsed_ms, "http_status": None}
        return result


def analyze_listing(listing, deal_score=None, user_prefs=None, system_prompt=None) -> dict:
    """
    Call Claude API to generate a Deal Brief for a listing.

    Returns:
        {
            "summary": str,       # 1-sentence verdict
            "strengths": str,     # what's good
            "concerns": str,      # what to watch out for
            "negotiation": str,   # leverage points + suggested offer
            "verdict": str,       # "strong_buy" | "worth_considering" | "pass"
        }
    """
    context = build_listing_context(listing, deal_score, user_prefs)

    if system_prompt is None:
        from config import DEFAULT_PROMPTS
        system_prompt = DEFAULT_PROMPTS["deal"]

    user_message = f"""Analyze this listing for my buyer:

{context}

Remember: be specific, reference real numbers, and give an actual dollar amount for the suggested opening offer.
If the buyer profile is provided, tailor your analysis to their specific situation, lifestyle, and priorities."""

    return _call_anthropic(system_prompt, user_message)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  PORTFOLIO / SET ANALYSIS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def analyze_portfolio(listings, user_composites: dict, user_prefs: dict,
                      flag_label: str = "selected", system_prompt=None) -> dict:
    """
    Call Claude API to generate a big-picture analysis of a set of listings.

    Args:
        listings: list of Listing objects
        user_composites: dict of listing_id -> composite score
        user_prefs: dict from user.get_prefs()
        flag_label: "Favorites", "Maybes", or "Hidden" for context

    Returns:
        {
            "headline": str,          # bold opening takeaway
            "ranking": str,           # ranked list with reasoning
            "patterns": str,          # trends, common strengths/weaknesses
            "strategy": str,          # what to do next, negotiation plays
            "dark_horse": str,        # underrated pick or contrarian take
            "bottom_line": str,       # final recommendation
        }
    """
    system_context, user_message = build_portfolio_context(
        listings, user_composites, user_prefs, flag_label
    )

    if system_prompt is None:
        from config import DEFAULT_PROMPTS
        base_prompt = DEFAULT_PROMPTS["portfolio"]
    else:
        base_prompt = system_prompt

    # Replace the placeholder with the actual base prompt
    final_system_prompt = system_context.replace("{{BASE_PROMPT}}", base_prompt)

    return _call_anthropic(final_system_prompt, user_message,
                           max_tokens=2048, timeout=60)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  PREFERENCES ANALYSIS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def analyze_preferences(prefs: dict, defaults: dict, system_prompt=None) -> dict:
    """
    Call Claude API to analyze a user's scoring preferences configuration.

    Args:
        prefs: dict of current preference values (imp_* weights, price range, etc.)
        defaults: dict of default preference values for comparison

    Returns:
        {
            "headline": str,        # one-sentence overall assessment
            "strengths": str,       # what's well-configured
            "blind_spots": str,     # what they might be missing
            "tweaks": str,          # specific slider suggestions
            "local_insight": str,   # market-specific advice
            "bottom_line": str,     # final recommendation
        }
    """
    context = build_preferences_context(prefs, defaults)

    if system_prompt is None:
        from config import DEFAULT_PROMPTS
        system_prompt = DEFAULT_PROMPTS["preferences"]

    user_message = f"""Review this buyer's scoring configuration and give me honest feedback:

{context}"""

    return _call_anthropic(system_prompt, user_message,
                           max_tokens=1536, timeout=45)
