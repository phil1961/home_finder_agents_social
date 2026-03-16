# ─────────────────────────────────────────────
# File: app/services/billing.py
# App Version: 2026.03.14 | File Version: 1.0.0
# Last Modified: 2026-03-14
# ─────────────────────────────────────────────
"""
app/services/billing.py
────────────────────────
Billing tiers, usage quota enforcement, and budget alerts for HomeFinder Social.

Each site in the registry has a billing plan (free/basic/pro/unlimited) with
per-type call limits and a monthly dollar budget cap.  The pipeline, AI routes,
and detail-enrichment routes call ``check_quota()`` before making paid API
calls; if the site has exceeded its limits the call is blocked with a
human-readable reason.

All data lives in two places:
  - registry.db  (billing plan + limits — raw sqlite3)
  - per-site DB  (ApiCallLog rows — SQLAlchemy ORM)
"""

import logging
from datetime import datetime, timezone, timedelta

log = logging.getLogger(__name__)

# ── Plan tier defaults ────────────────────────────────────────────────────────

PLAN_DEFAULTS = {
    "free": {
        "monthly_limit_ai": 10,
        "monthly_limit_fetch": 50,
        "monthly_budget": 1.00,
    },
    "basic": {
        "monthly_limit_ai": 100,
        "monthly_limit_fetch": 500,
        "monthly_budget": 10.00,
    },
    "pro": {
        "monthly_limit_ai": 500,
        "monthly_limit_fetch": 2000,
        "monthly_budget": 50.00,
    },
    "unlimited": {
        "monthly_limit_ai": 0,
        "monthly_limit_fetch": 0,
        "monthly_budget": 0,
    },
}

# Call types classified as AI vs fetch for quota buckets
AI_CALL_TYPES = {"anthropic_deal", "anthropic_portfolio", "anthropic_prefs"}
FETCH_CALL_TYPES = {
    "zillow", "realtor", "zillow_detail", "realtor_detail",
    "google_places", "google_geocode",
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _billing_cycle_start(cycle_day: int = 1) -> datetime:
    """Return the start of the current billing cycle as a UTC datetime.

    ``cycle_day`` is the day-of-month the cycle resets (1-28).
    If today is before that day we go back to the previous month.
    """
    now = datetime.now(timezone.utc)
    cycle_day = max(1, min(cycle_day, 28))
    try:
        start = now.replace(day=cycle_day, hour=0, minute=0, second=0, microsecond=0)
    except ValueError:
        # Shouldn't happen with clamp to 28, but be safe
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if start > now:
        # Roll back one month
        if start.month == 1:
            start = start.replace(year=start.year - 1, month=12)
        else:
            start = start.replace(month=start.month - 1)
    return start


def _get_site_billing(site_key: str) -> dict:
    """Return billing fields from registry for the given site_key."""
    from app.services.registry import get_site_any
    site = get_site_any(site_key)
    if not site:
        return {}
    return {
        "billing_plan": site.get("billing_plan") or "free",
        "monthly_budget": site.get("monthly_budget") or 0,
        "monthly_limit_ai": site.get("monthly_limit_ai") or 0,
        "monthly_limit_fetch": site.get("monthly_limit_fetch") or 0,
        "billing_email": site.get("billing_email") or "",
        "billing_cycle_start": site.get("billing_cycle_start") or 1,
    }


# ── Public API ────────────────────────────────────────────────────────────────

def get_site_usage(site_key: str) -> dict:
    """Return current billing-cycle usage for *site_key*.

    Returns::

        {
            "ai_calls": int,
            "fetch_calls": int,
            "total_cost": float,
            "cycle_start": datetime,
        }
    """
    from app.models import ApiCallLog, db
    from sqlalchemy import func

    billing = _get_site_billing(site_key)
    cycle_start = _billing_cycle_start(billing.get("billing_cycle_start", 1))

    rows = (
        db.session.query(
            ApiCallLog.call_type,
            func.count(ApiCallLog.id).label("cnt"),
        )
        .filter(
            ApiCallLog.site_key == site_key,
            ApiCallLog.called_at >= cycle_start,
        )
        .group_by(ApiCallLog.call_type)
        .all()
    )

    cost_map = ApiCallLog.COST_MAP
    ai_calls = 0
    fetch_calls = 0
    total_cost = 0.0

    for call_type, cnt in rows:
        total_cost += cnt * cost_map.get(call_type, 0)
        if call_type in AI_CALL_TYPES:
            ai_calls += cnt
        elif call_type in FETCH_CALL_TYPES:
            fetch_calls += cnt

    return {
        "ai_calls": ai_calls,
        "fetch_calls": fetch_calls,
        "total_cost": round(total_cost, 4),
        "cycle_start": cycle_start,
    }


def check_quota(site_key: str, call_type: str) -> tuple[bool, str | None]:
    """Check whether the site may make another API call of *call_type*.

    Returns ``(True, None)`` if allowed, or ``(False, reason)`` if blocked.
    """
    billing = _get_site_billing(site_key)
    plan = billing.get("billing_plan", "free")

    # Unlimited plan — always allowed
    if plan == "unlimited":
        return True, None

    usage = get_site_usage(site_key)

    # Per-type limit check
    if call_type in AI_CALL_TYPES:
        limit = billing.get("monthly_limit_ai", 0)
        if limit > 0 and usage["ai_calls"] >= limit:
            return False, (
                f"Monthly AI analysis limit reached ({limit} calls). "
                f"Upgrade your plan or wait for the next billing cycle."
            )
    elif call_type in FETCH_CALL_TYPES:
        limit = billing.get("monthly_limit_fetch", 0)
        if limit > 0 and usage["fetch_calls"] >= limit:
            return False, (
                f"Monthly fetch limit reached ({limit} calls). "
                f"Upgrade your plan or wait for the next billing cycle."
            )

    # Budget cap check
    budget = billing.get("monthly_budget", 0)
    if budget > 0 and usage["total_cost"] >= budget:
        return False, (
            f"Monthly budget cap reached (${budget:.2f}). "
            f"Upgrade your plan or increase the budget."
        )

    # ── Fire alerts at 80% and 100% thresholds ───────────────────
    if budget > 0:
        pct = usage["total_cost"] / budget * 100
        if pct >= 100:
            _maybe_send_alert(site_key, billing, 100)
        elif pct >= 80:
            _maybe_send_alert(site_key, billing, 80)

    return True, None


def get_billing_info(site_key: str) -> dict:
    """Return a rich dict suitable for the billing settings page.

    Merges plan defaults, registry overrides, and live usage into one payload.
    """
    billing = _get_site_billing(site_key)
    usage = get_site_usage(site_key)
    plan = billing.get("billing_plan", "free")
    defaults = PLAN_DEFAULTS.get(plan, PLAN_DEFAULTS["free"])

    limit_ai = billing.get("monthly_limit_ai", 0)
    limit_fetch = billing.get("monthly_limit_fetch", 0)
    budget = billing.get("monthly_budget", 0)

    def _pct(used, limit):
        if not limit or limit <= 0:
            return 0
        return min(round(used / limit * 100, 1), 100)

    return {
        "plan": plan,
        "plan_defaults": defaults,
        "monthly_limit_ai": limit_ai,
        "monthly_limit_fetch": limit_fetch,
        "monthly_budget": budget,
        "billing_email": billing.get("billing_email", ""),
        "billing_cycle_start": billing.get("billing_cycle_start", 1),
        # Live usage
        "ai_calls": usage["ai_calls"],
        "fetch_calls": usage["fetch_calls"],
        "total_cost": usage["total_cost"],
        "cycle_start": usage["cycle_start"],
        # Percentages for progress bars
        "ai_pct": _pct(usage["ai_calls"], limit_ai),
        "fetch_pct": _pct(usage["fetch_calls"], limit_fetch),
        "budget_pct": _pct(usage["total_cost"], budget),
    }


def send_budget_alert(site_key: str, pct: int):
    """Send a budget alert email for the given threshold percentage.

    Called internally when usage crosses the 80% or 100% mark.
    """
    billing = _get_site_billing(site_key)
    email = billing.get("billing_email")
    if not email:
        log.info(f"[billing] No billing_email for {site_key}, skipping {pct}%% alert")
        return

    try:
        from flask_mail import Message
        from app import mail

        subject = f"HomeFinder budget alert — {pct}% of monthly limit ({site_key})"
        usage = get_site_usage(site_key)
        budget = billing.get("monthly_budget", 0)

        body = (
            f"Your HomeFinder site '{site_key}' has reached {pct}% of its "
            f"monthly budget (${budget:.2f}).\n\n"
            f"Current spend: ${usage['total_cost']:.2f}\n"
            f"AI calls: {usage['ai_calls']}\n"
            f"Fetch calls: {usage['fetch_calls']}\n\n"
        )
        if pct >= 100:
            body += (
                "API calls are now BLOCKED until the next billing cycle resets "
                "or you upgrade your plan.\n"
            )
        else:
            body += (
                "Consider upgrading your plan or adjusting usage before the cap "
                "is reached.\n"
            )

        msg = Message(subject=subject, recipients=[email], body=body)
        mail.send(msg)
        log.info(f"[billing] Sent {pct}%% budget alert to {email} for {site_key}")
    except Exception as exc:
        log.warning(f"[billing] Failed to send budget alert for {site_key}: {exc}")


# ── Internal alert dedup ──────────────────────────────────────────────────────
# Simple in-memory dedup so we don't spam on every single request.
_alert_sent: dict[str, datetime] = {}


def _maybe_send_alert(site_key: str, billing: dict, pct: int):
    """Send a budget alert only once per threshold per billing cycle."""
    key = f"{site_key}:{pct}"
    last = _alert_sent.get(key)
    cycle_start = _billing_cycle_start(billing.get("billing_cycle_start", 1))
    if last and last >= cycle_start:
        return  # already sent this cycle
    _alert_sent[key] = datetime.now(timezone.utc)
    send_budget_alert(site_key, pct)
