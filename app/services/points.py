# ─────────────────────────────────────────────
# File: app/services/points.py
# App Version: 2026.03.14 | File Version: 1.0.0
# Last Modified: 2026-03-14
# ─────────────────────────────────────────────
"""Points system: award, query, and enforce daily caps."""
import logging
from datetime import datetime, timezone, timedelta

from app.models import db
from app.models_social import UserPoints, UserPointLog

log = logging.getLogger(__name__)

DAILY_CAP = 50  # max points earnable per day

POINT_VALUES = {
    "share_listing": 1,
    "reaction_received": 3,
    "collection_created": 2,
    "referral_registered": 10,
    "friend_listing": 5,
    "listing_created": 5,
    "listing_approved": 3,
}


def award_points(user_id, delta, reason, reference_id=None):
    """Award *delta* points to *user_id*.

    Enforces a daily cap of DAILY_CAP points. Returns the actual points
    awarded (may be less than delta if cap is reached), or 0 if capped.
    """
    if not user_id or delta <= 0:
        return 0

    # Check daily cap
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    earned_today = db.session.query(
        db.func.coalesce(db.func.sum(UserPointLog.delta), 0)
    ).filter(
        UserPointLog.user_id == user_id,
        UserPointLog.created_at >= today_start,
    ).scalar()

    remaining = max(0, DAILY_CAP - earned_today)
    if remaining <= 0:
        log.debug(f"Points cap reached for user {user_id}")
        return 0

    actual = min(delta, remaining)

    # Upsert UserPoints
    account = UserPoints.query.filter_by(user_id=user_id).first()
    if not account:
        account = UserPoints(user_id=user_id, balance=0, lifetime_earned=0)
        db.session.add(account)

    account.balance += actual
    account.lifetime_earned += actual

    # Log entry
    entry = UserPointLog(
        user_id=user_id,
        delta=actual,
        reason=reason,
        reference_id=reference_id,
    )
    db.session.add(entry)
    db.session.commit()

    log.info(f"Awarded {actual} pts to user {user_id} ({reason})")
    return actual


def get_balance(user_id):
    """Return current points balance for user_id, or 0."""
    if not user_id:
        return 0
    account = UserPoints.query.filter_by(user_id=user_id).first()
    return account.balance if account else 0
