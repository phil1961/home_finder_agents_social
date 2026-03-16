# ─────────────────────────────────────────────
# File: app/routes/tour_routes.py
# App Version: 2026.03.12 | File Version: 1.1.0
# Last Modified: 2026-03-12
# ─────────────────────────────────────────────
"""
app/routes/tour_routes.py — Tour, notes, contact, and help routes.
"""
from flask import render_template, request, redirect, flash, jsonify, current_app
from flask_login import login_required, current_user

from app.models import db, Listing
from app.routes.dashboard_helpers import dashboard_bp, _site_redirect


@dashboard_bp.route("/listing/<int:listing_id>/note", methods=["POST"])
@login_required
def save_note(listing_id):
    """AJAX — upsert a ListingNote for the current user."""
    from datetime import datetime, timezone
    from app.models import ListingNote

    listing = db.session.get(Listing, listing_id)
    if not listing:
        return jsonify({"error": "Listing not found"}), 404

    note = ListingNote.query.filter_by(
        user_id=current_user.id, listing_id=listing_id
    ).first()
    if not note:
        note = ListingNote(user_id=current_user.id, listing_id=listing_id)
        db.session.add(note)

    note.note_text       = request.form.get("note_text", "")[:3000]
    note.visited         = request.form.get("visited")         == "true"
    note.scheduled_visit = request.form.get("scheduled_visit") == "true"
    note.not_interested  = request.form.get("not_interested")  == "true"
    note.made_offer      = request.form.get("made_offer")      == "true"
    note.updated_at      = datetime.now(timezone.utc)
    db.session.commit()

    return jsonify({"ok": True, "updated_at": note.updated_at.strftime("%b %d, %I:%M %p")})


# ── Tour Itinerary ────────────────────────────────────────────

@dashboard_bp.route("/itinerary")
@login_required
def itinerary():
    """Tour planner — favorites with notes and a Google Maps route builder."""
    from app.models import ListingNote, UserFlag

    # Gather all flagged listings for this user
    flags = UserFlag.query.filter_by(user_id=current_user.id).all()
    fav_ids    = [f.listing_id for f in flags if f.flag == "favorite"]
    maybe_ids  = [f.listing_id for f in flags if f.flag == "maybe"]

    def fetch_with_notes(listing_ids):
        if not listing_ids:
            return []
        listings = Listing.query.filter(
            Listing.id.in_(listing_ids),
            Listing.status == "active"
        ).all()
        notes_map = {
            n.listing_id: n
            for n in ListingNote.query.filter(
                ListingNote.user_id == current_user.id,
                ListingNote.listing_id.in_(listing_ids)
            ).all()
        }
        return [(l, notes_map.get(l.id)) for l in listings]

    favorites = fetch_with_notes(fav_ids)
    maybes    = fetch_with_notes(maybe_ids)

    # Sort: scheduled -> unvisited -> visited -> not_interested
    def sort_key(pair):
        note = pair[1]
        if not note:                 return 1
        if note.made_offer:          return 0
        if note.scheduled_visit:     return 1
        if note.visited:             return 3
        if note.not_interested:      return 4
        return 2

    favorites.sort(key=sort_key)
    maybes.sort(key=sort_key)

    return render_template(
        "dashboard/itinerary.html",
        favorites=favorites,
        maybes=maybes,
        user=current_user,
    )


# ── Client: Contact Agent ────────────────────────────────────────

@dashboard_bp.route("/contact-agent", methods=["POST"])
@login_required
def contact_agent():
    """Client sends a message to their agent via email."""
    from flask_mail import Message
    from app import mail

    if not current_user.agent_id:
        flash("No agent assigned.", "warning")
        return _site_redirect("dashboard.index")

    agent_profile = current_user.assigned_agent
    if not agent_profile or not agent_profile.user:
        flash("Could not find your agent. Please contact support.", "danger")
        return _site_redirect("dashboard.index")

    message_body = request.form.get("message", "").strip()
    if not message_body:
        flash("Please enter a message.", "warning")
        return redirect(request.referrer or _site_redirect("dashboard.index").location)

    try:
        msg = Message(
            subject=f"HomeFinder Message from {current_user.username}",
            recipients=[agent_profile.user.email],
            reply_to=current_user.email,
            html=f"""
            <div style="font-family: sans-serif; max-width: 480px; margin: 0 auto; padding: 20px;">
                <h3 style="color: #1e3a5f;">Message from your client</h3>
                <p><strong>From:</strong> {current_user.username} ({current_user.email})</p>
                <hr>
                <p style="white-space: pre-wrap;">{message_body}</p>
                <hr>
                <p style="color: #9ca3af; font-size: 12px;">
                    Sent via HomeFinder. Reply directly to this email to respond to your client.
                </p>
            </div>
            """,
        )
        mail.send(msg)
        flash(f"Message sent to {agent_profile.full_name}.", "success")
    except Exception as exc:
        current_app.logger.error(f"Contact agent email failed: {exc}")
        flash("Failed to send message. Please try again or contact your agent directly.", "danger")

    return redirect(request.referrer or _site_redirect("dashboard.index").location)


# ── Help and Why pages ────────────────────────────────────────────

@dashboard_bp.route("/why/user")
def why_user():
    return render_template("dashboard/why_user.html", user=current_user)

@dashboard_bp.route("/why/agent")
def why_agent():
    return render_template("dashboard/why_agent.html", user=current_user)

@dashboard_bp.route("/why/owner")
def why_owner():
    if not current_user.is_authenticated or not current_user.is_owner:
        return _site_redirect("dashboard.why_user")
    return render_template("dashboard/why_owner.html", user=current_user)


@dashboard_bp.route("/help")
def help_page():
    """User help and feature guide."""
    return render_template("dashboard/help.html", user=current_user)
