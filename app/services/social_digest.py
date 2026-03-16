# ─────────────────────────────────────────────
# File: app/services/social_digest.py
# App Version: 2026.03.14 | File Version: 1.0.0
# Last Modified: 2026-03-14
# ─────────────────────────────────────────────
"""Weekly social digest email service."""
import logging
from datetime import datetime, timezone, timedelta

from flask import render_template
from flask_mail import Message

from app.models import db, User
from app.models_social import SocialShare, SocialReaction
from app import mail

log = logging.getLogger(__name__)


def send_weekly_digests(site_key):
    """Send weekly social digest emails to users with activity in the last 7 days.

    Returns the number of emails sent.
    """
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    sent_count = 0

    # Find users who had social activity in the last week
    users = User.query.filter(User.is_verified == True).all()

    for user in users:
        # Shares sent this week
        shares_sent = SocialShare.query.filter(
            SocialShare.sharer_id == user.id,
            SocialShare.created_at >= week_ago,
        ).count()

        # Shares received this week
        shares_received = SocialShare.query.filter(
            SocialShare.recipient_email == user.email,
            SocialShare.created_at >= week_ago,
        ).count()

        # Reactions received on user's shares this week
        reactions_received = db.session.query(SocialReaction).join(
            SocialShare, SocialReaction.share_id == SocialShare.id
        ).filter(
            SocialShare.sharer_id == user.id,
            SocialReaction.created_at >= week_ago,
        ).count()

        # Skip users with no activity
        if shares_sent == 0 and shares_received == 0 and reactions_received == 0:
            continue

        try:
            msg = Message(
                subject="Your Weekly HomeFinder Social Digest",
                recipients=[user.email],
                html=render_template(
                    "email/social_digest.html",
                    user=user,
                    shares_sent=shares_sent,
                    shares_received=shares_received,
                    reactions_received=reactions_received,
                    week_start=(week_ago).strftime("%b %d"),
                    week_end=datetime.now(timezone.utc).strftime("%b %d, %Y"),
                ),
            )
            mail.send(msg)
            sent_count += 1
        except Exception as exc:
            log.warning(f"Failed to send digest to {user.email}: {exc}")

    log.info(f"Social digest: sent {sent_count} emails for site {site_key}")
    return sent_count
