# ─────────────────────────────────────────────
# File: app/services/street_watch.py
# App Version: 2026.03.12 | File Version: 1.2.0
# Last Modified: 2026-03-13
# ─────────────────────────────────────────────
"""
Street Watch — business logic for monitoring streets for new listings,
price drops, and status changes.
"""
import logging
import re
import secrets
from datetime import datetime, timezone

from app.models import db

log = logging.getLogger(__name__)

# ── Street name suffix normalisation map ──────────────────────────────────
_SUFFIX_MAP = {
    "DRIVE": "DR", "DR": "DR",
    "STREET": "ST", "ST": "ST",
    "LANE": "LN", "LN": "LN",
    "COURT": "CT", "CT": "CT",
    "BOULEVARD": "BLVD", "BLVD": "BLVD",
    "AVENUE": "AVE", "AVE": "AVE",
    "WAY": "WAY",
    "CIRCLE": "CIR", "CIR": "CIR",
    "PLACE": "PL", "PL": "PL",
    "ROAD": "RD", "RD": "RD",
    "TERRACE": "TER", "TER": "TER",
    "PARKWAY": "PKWY", "PKWY": "PKWY",
    "HIGHWAY": "HWY", "HWY": "HWY",
    "TRAIL": "TRL", "TRL": "TRL",
    "CROSSING": "XING", "XING": "XING",
    "RUN": "RUN",
    "PATH": "PATH",
    "POINT": "PT", "PT": "PT",
    "LOOP": "LOOP",
    "COVE": "CV", "CV": "CV",
}

# House number pattern: digits optionally followed by a letter, then space
_HOUSE_NUM_RE = re.compile(r"^\d+[A-Za-z]?\s+")


def extract_street_name(address: str):
    """Extract and normalise a street name from a full address.

    Returns (normalised, display) — e.g. ("OAK DR", "Oak Dr").
    Returns (None, None) if extraction fails.
    """
    if not address:
        return None, None

    # Take first comma-separated segment
    segment = address.split(",")[0].strip()
    if not segment:
        return None, None

    # Strip leading house number
    street = _HOUSE_NUM_RE.sub("", segment).strip()
    if not street:
        return None, None

    # Normalise suffix
    words = street.upper().split()
    if words:
        last = words[-1]
        if last in _SUFFIX_MAP:
            words[-1] = _SUFFIX_MAP[last]

    normalised = " ".join(words)
    # Display version: title-case but keep directionals and suffix uppercase
    display_words = []
    for w in normalised.split():
        if w in _SUFFIX_MAP.values() or w in ("N", "S", "E", "W", "NE", "NW", "SE", "SW"):
            display_words.append(w)
        else:
            display_words.append(w.title())
    display = " ".join(display_words)

    return normalised, display


def create_watch(email, street_name, zip_code, user_id=None):
    """Create a new street watch or return existing active one.

    Returns (StreetWatch, created:bool).
    """
    from app.models import StreetWatch

    email = email.strip().lower()
    normalised, display = extract_street_name(street_name)
    if not normalised:
        # If already normalised (e.g. from quick-add), use as-is
        normalised = street_name.upper().strip()
        display = street_name.strip().title()

    # Check for existing watch (active or inactive — unique constraint covers both)
    existing = StreetWatch.query.filter_by(
        email=email, street_name=normalised, zip_code=zip_code
    ).first()
    if existing:
        if existing.is_active:
            # Ensure user_id is linked if caller provides one
            if user_id and existing.user_id != user_id:
                existing.user_id = user_id
                db.session.commit()
                log.info(f"Linked existing watch #{existing.id} to user #{user_id}")
            return existing, False
        # Reactivate a previously deactivated watch
        existing.is_active = True
        existing.user_id = user_id or existing.user_id
        existing.unsubscribe_token = secrets.token_urlsafe(32)
        db.session.commit()
        log.info(f"Reactivated street watch: {email} → {normalised} ({zip_code})")
        return existing, True

    watch = StreetWatch(
        email=email,
        user_id=user_id,
        street_name=normalised,
        zip_code=zip_code,
        label=display,
        is_active=True,
        unsubscribe_token=secrets.token_urlsafe(32),
    )
    db.session.add(watch)
    db.session.commit()
    log.info(f"Created street watch: {email} → {normalised} ({zip_code})")
    return watch, True


def deactivate_watch(watch_id, email=None, user_id=None):
    """Deactivate a watch with ownership check. Returns True on success."""
    from app.models import StreetWatch

    watch = db.session.get(StreetWatch, watch_id)
    if not watch:
        return False

    # Ownership check
    if user_id and watch.user_id == user_id:
        pass  # OK
    elif email and watch.email == email.lower():
        pass  # OK
    else:
        return False

    watch.is_active = False
    db.session.commit()
    log.info(f"Deactivated street watch #{watch_id}")
    return True


def deactivate_by_token(token):
    """Deactivate a watch by unsubscribe token. Returns True on success."""
    from app.models import StreetWatch

    watch = StreetWatch.query.filter_by(
        unsubscribe_token=token, is_active=True
    ).first()
    if not watch:
        return False

    watch.is_active = False
    db.session.commit()
    log.info(f"Unsubscribed street watch #{watch.id} via token")
    return True


def link_watches_to_user(email, user_id):
    """Link all watches for an email to a user account (called at registration)."""
    from app.models import StreetWatch

    email = email.strip().lower()
    watches = StreetWatch.query.filter_by(email=email, user_id=None).all()
    for w in watches:
        w.user_id = user_id
    if watches:
        db.session.commit()
        log.info(f"Linked {len(watches)} street watches to user #{user_id}")


def get_user_watches(user_id=None, email=None):
    """Get active watches for a user or guest email."""
    from app.models import StreetWatch

    if user_id:
        return StreetWatch.query.filter_by(
            user_id=user_id, is_active=True
        ).order_by(StreetWatch.created_at.desc()).all()
    if email:
        return StreetWatch.query.filter_by(
            email=email.strip().lower(), is_active=True
        ).order_by(StreetWatch.created_at.desc()).all()
    return []


def check_watches_after_pipeline(watch_events, site_key):
    """Match pipeline events against active watches, create alert rows.

    watch_events: list of dicts with keys:
        listing_id, address, zip_code, alert_type ('new_listing'|'price_drop'|'back_on_market'),
        detail_json (optional dict)
    """
    from app.models import StreetWatch, StreetWatchAlert
    import json

    if not watch_events:
        return 0

    alert_count = 0
    for event in watch_events:
        normalised, _ = extract_street_name(event.get("address", ""))
        if not normalised:
            continue
        zip_code = event.get("zip_code", "")

        # Find matching active watches
        matches = StreetWatch.query.filter_by(
            zip_code=zip_code, street_name=normalised, is_active=True
        ).all()

        for watch in matches:
            # Idempotent: unique constraint on (watch_id, listing_id, alert_type)
            existing = StreetWatchAlert.query.filter_by(
                watch_id=watch.id,
                listing_id=event["listing_id"],
                alert_type=event["alert_type"],
            ).first()
            if existing:
                continue

            alert = StreetWatchAlert(
                watch_id=watch.id,
                listing_id=event["listing_id"],
                alert_type=event["alert_type"],
                detail_json=json.dumps(event.get("detail", {})),
            )
            db.session.add(alert)
            alert_count += 1

    if alert_count:
        db.session.commit()
        log.info(f"Created {alert_count} street watch alerts for site '{site_key}'")

    return alert_count


def send_watch_digests(site_key):
    """Send email digests for pending (un-emailed) alerts, grouped by email."""
    from app.models import StreetWatch, StreetWatchAlert, Listing
    from flask import current_app, render_template
    from app import mail
    from flask_mail import Message

    # Get all pending alerts (emailed_at IS NULL) with active watches
    pending = (
        db.session.query(StreetWatchAlert)
        .join(StreetWatch, StreetWatchAlert.watch_id == StreetWatch.id)
        .filter(StreetWatchAlert.emailed_at.is_(None))
        .filter(StreetWatch.is_active.is_(True))
        .all()
    )

    if not pending:
        return 0

    # Group by watch email
    by_email = {}
    for alert in pending:
        email = alert.watch.email
        by_email.setdefault(email, []).append(alert)

    sent_count = 0
    for email, alerts in by_email.items():
        # Gather listing data for the template
        alert_data = []
        for alert in alerts:
            listing = db.session.get(Listing, alert.listing_id)
            if not listing:
                continue
            alert_data.append({
                "alert": alert,
                "listing": listing,
                "street_label": alert.watch.label,
                "unsubscribe_token": alert.watch.unsubscribe_token,
            })

        if not alert_data:
            continue

        try:
            html_body = render_template(
                "email/street_watch_digest.html",
                alerts=alert_data,
                site_key=site_key,
            )
            msg = Message(
                subject=f"Street Watch Alert — {len(alert_data)} new update{'s' if len(alert_data) != 1 else ''}",
                recipients=[email],
                html=html_body,
            )
            mail.send(msg)

            # Stamp emailed_at
            now = datetime.now(timezone.utc)
            for alert in alerts:
                alert.emailed_at = now
            db.session.commit()
            sent_count += 1
            log.info(f"Sent street watch digest to {email}: {len(alert_data)} alerts")

        except Exception as exc:
            log.warning(f"Failed to send street watch digest to {email}: {exc}")

    return sent_count
