# ─────────────────────────────────────────────
# File: app/routes/social.py
# App Version: 2026.03.14 | File Version: 1.1.0
# Last Modified: 2026-03-14
# ─────────────────────────────────────────────
"""Social feature routes: sharing, collections, reactions, referrals."""
import logging
from datetime import datetime, timezone

from flask import (
    Blueprint, render_template, redirect, url_for, flash, request,
    current_app, g, session, jsonify, abort,
)
from flask_login import login_required, current_user
from flask_mail import Message

from app.models import db, User, Listing
from app.models_social import (
    SocialShare, SocialReaction, SocialCollection,
    SocialCollectionItem, Referral, REACTION_TYPES,
    UserPoints, UserPointLog, FriendListing,
)
from app import mail
from app.utils import site_redirect as _site_redirect, site_url as _site_url

log = logging.getLogger(__name__)

social_bp = Blueprint("social", __name__, url_prefix="/social")


def _share_url(token):
    """Build a share URL with the correct /site/<key> prefix."""
    site = getattr(g, "site", None)
    if site:
        script = request.script_root or ""
        return f"{request.host_url.rstrip('/')}{script}/site/{site['site_key']}/social/s/{token}"
    return url_for("social.view_share", token=token, _external=True)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  SHARING
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@social_bp.route("/share", methods=["POST"])
def share_listing():
    """Share a listing with someone via email/link."""
    listing_id = request.form.get("listing_id", type=int)
    recipient_email = request.form.get("recipient_email", "").strip()
    recipient_name = request.form.get("recipient_name", "").strip()
    relationship = request.form.get("relationship", "friend")
    message = request.form.get("message", "").strip()

    if not listing_id or not recipient_email:
        flash("Please provide a listing and recipient email.", "warning")
        return redirect(request.referrer or _site_url("dashboard.index"))

    listing = db.session.get(Listing, listing_id)
    if not listing:
        flash("Listing not found.", "danger")
        return redirect(request.referrer or _site_url("dashboard.index"))

    # Build the share
    share = SocialShare(
        listing_id=listing_id,
        share_type="listing",
        recipient_email=recipient_email,
        recipient_name=recipient_name or None,
        relationship=relationship,
        message=message or None,
        share_token=SocialShare.generate_token(),
    )

    # Set sharer info — use the name from the form (user can customize it)
    form_name = request.form.get("sharer_name", "").strip()
    if current_user.is_authenticated:
        share.sharer_id = current_user.id
        share.sharer_name = form_name or current_user.username
        share.sharer_email = current_user.email
    else:
        share.sharer_name = form_name or "Someone"
        share.sharer_email = request.form.get("sharer_email", "").strip()

    db.session.add(share)
    db.session.commit()

    # Award points for sharing
    if share.sharer_id:
        try:
            from app.services.points import award_points
            award_points(share.sharer_id, 1, "share_listing", reference_id=share.id)
        except Exception:
            pass

    # Send email notification
    _send_share_email(share, listing)

    flash(f"Listing shared with {recipient_name or recipient_email}!", "success")
    return redirect(request.referrer or _site_url("dashboard.index"))


@social_bp.route("/s/<token>")
def view_share(token):
    """Landing page for a shared listing."""
    share = SocialShare.query.filter_by(share_token=token).first_or_404()
    share.mark_viewed()
    db.session.commit()

    listing = share.listing
    collection = share.collection

    # If the recipient is logged in, link them
    if current_user.is_authenticated and not share.recipient_user_id:
        if current_user.email.lower() == share.recipient_email.lower():
            share.recipient_user_id = current_user.id
            db.session.commit()

    # Auto-favorite the shared listing so it appears in Favorites on the dashboard
    if listing:
        if current_user.is_authenticated:
            from app.models import UserFlag
            existing = UserFlag.query.filter_by(
                user_id=current_user.id, listing_id=listing.id
            ).first()
            if not existing:
                uf = UserFlag(user_id=current_user.id, listing_id=listing.id, flag="favorite")
                db.session.add(uf)
                db.session.commit()
        else:
            guest_flags = session.get("guest_flags", {})
            lid_key = str(listing.id)
            if lid_key not in guest_flags:
                guest_flags[lid_key] = "favorite"
                session["guest_flags"] = guest_flags
                session.modified = True
        # Set session hint so dashboard defaults to Favorites filter
        session["_default_flag"] = "favorite"
        session.modified = True

    return render_template(
        "social/share_landing.html",
        share=share,
        listing=listing,
        collection=collection,
        reaction_types=REACTION_TYPES,
    )


@social_bp.route("/react/<int:share_id>", methods=["POST"])
def react_to_share(share_id):
    """Add a reaction to a shared listing."""
    share = db.session.get(SocialShare, share_id)
    if not share:
        abort(404)

    reaction_type = request.form.get("reaction_type", "interested")
    comment = request.form.get("comment", "").strip()
    reactor_email = ""

    if current_user.is_authenticated:
        reactor_email = current_user.email
        reactor_user_id = current_user.id
    else:
        reactor_email = request.form.get("reactor_email", share.recipient_email or "")
        reactor_user_id = None

    # Check for existing reaction
    existing = SocialReaction.query.filter_by(
        share_id=share_id,
        reactor_email=reactor_email,
    ).first()

    is_new_reaction = False
    if existing:
        existing.reaction_type = reaction_type
        existing.comment = comment or existing.comment
    else:
        is_new_reaction = True
        reaction = SocialReaction(
            share_id=share_id,
            reactor_user_id=reactor_user_id,
            reactor_email=reactor_email,
            reaction_type=reaction_type,
            comment=comment or None,
        )
        db.session.add(reaction)

    share.status = "replied"
    db.session.commit()

    # Award points to sharer for new reactions
    if is_new_reaction and share.sharer_id:
        try:
            from app.services.points import award_points
            award_points(share.sharer_id, 3, "reaction_received", reference_id=share.id)
        except Exception:
            pass

    # Notify the sharer
    _send_reaction_email(share, reaction_type)

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"ok": True, "reaction": reaction_type})

    flash("Thanks for your feedback!", "success")
    return redirect(request.referrer or url_for("social.view_share", token=share.share_token))


@social_bp.route("/shared-with-me")
@login_required
def shared_with_me():
    """Dashboard of listings shared with the current user."""
    shares = SocialShare.query.filter_by(
        recipient_email=current_user.email,
    ).order_by(SocialShare.created_at.desc()).all()

    return render_template("social/shared_with_me.html", shares=shares)


@social_bp.route("/my-shares")
@login_required
def my_shares():
    """What I've shared + status tracking."""
    shares = SocialShare.query.filter_by(
        sharer_id=current_user.id,
    ).order_by(SocialShare.created_at.desc()).all()

    return render_template("social/my_shares.html", shares=shares)


@social_bp.route("/copy-link/<int:listing_id>")
def copy_link(listing_id):
    """Generate a shareable link for a listing (no email required)."""
    listing = db.session.get(Listing, listing_id)
    if not listing:
        abort(404)

    share = SocialShare(
        listing_id=listing_id,
        share_type="listing",
        recipient_email="link",  # placeholder for link-only shares
        share_token=SocialShare.generate_token(),
        sharer_id=current_user.id if current_user.is_authenticated else None,
        sharer_name=current_user.username if current_user.is_authenticated else "Someone",
    )
    db.session.add(share)
    db.session.commit()

    share_url = _share_url(share.share_token)
    return jsonify({"ok": True, "url": share_url})


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  COLLECTIONS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@social_bp.route("/collections")
@login_required
def collections_list():
    """Browse my collections."""
    collections = SocialCollection.query.filter_by(
        creator_id=current_user.id,
    ).order_by(SocialCollection.updated_at.desc()).all()

    return render_template("social/collections.html", collections=collections)


@social_bp.route("/collections/create", methods=["GET", "POST"])
@login_required
def collection_create():
    """Create a new collection."""
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        is_public = request.form.get("is_public") == "on"

        if not title:
            flash("Please give your collection a title.", "warning")
            return redirect(url_for("social.collection_create"))

        collection = SocialCollection(
            creator_id=current_user.id,
            title=title,
            description=description or None,
            share_token=SocialShare.generate_token(),
            is_public=is_public,
        )
        db.session.add(collection)
        db.session.commit()

        # Award points for creating a collection
        try:
            from app.services.points import award_points
            award_points(current_user.id, 2, "collection_created", reference_id=collection.id)
        except Exception:
            pass

        flash(f"Collection '{title}' created!", "success")
        return _site_redirect("social.collection_detail", collection_id=collection.id)

    return render_template("social/collection_create.html")


@social_bp.route("/collections/<int:collection_id>")
@login_required
def collection_detail(collection_id):
    """View a collection."""
    collection = db.session.get(SocialCollection, collection_id)
    if not collection:
        abort(404)

    # Only the creator or public collections
    if collection.creator_id != current_user.id and not collection.is_public:
        abort(403)

    return render_template("social/collection_detail.html", collection=collection)


@social_bp.route("/c/<token>")
def collection_public(token):
    """Public view of a shared collection."""
    collection = SocialCollection.query.filter_by(share_token=token).first_or_404()
    collection.view_count += 1
    db.session.commit()

    return render_template("social/collection_public.html", collection=collection)


@social_bp.route("/collections/<int:collection_id>/add", methods=["POST"])
@login_required
def collection_add_listing(collection_id):
    """Add a listing to a collection."""
    collection = db.session.get(SocialCollection, collection_id)
    if not collection or collection.creator_id != current_user.id:
        abort(404)

    listing_id = request.form.get("listing_id", type=int)
    note = request.form.get("note", "").strip()

    if not listing_id:
        flash("No listing specified.", "warning")
        return redirect(request.referrer or _site_url("dashboard.index"))

    # Check if already in collection
    existing = SocialCollectionItem.query.filter_by(
        collection_id=collection_id,
        listing_id=listing_id,
    ).first()
    if existing:
        flash("Listing is already in this collection.", "info")
    else:
        max_pos = db.session.query(
            db.func.coalesce(db.func.max(SocialCollectionItem.position), 0)
        ).filter_by(collection_id=collection_id).scalar()

        item = SocialCollectionItem(
            collection_id=collection_id,
            listing_id=listing_id,
            note=note or None,
            position=max_pos + 1,
        )
        db.session.add(item)
        db.session.commit()
        flash("Listing added to collection!", "success")

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"ok": True})

    return redirect(request.referrer or _site_url("dashboard.index"))


@social_bp.route("/collections/<int:collection_id>/remove/<int:item_id>", methods=["POST"])
@login_required
def collection_remove_listing(collection_id, item_id):
    """Remove a listing from a collection."""
    collection = db.session.get(SocialCollection, collection_id)
    if not collection or collection.creator_id != current_user.id:
        abort(404)

    item = db.session.get(SocialCollectionItem, item_id)
    if item and item.collection_id == collection_id:
        db.session.delete(item)
        db.session.commit()
        flash("Listing removed from collection.", "info")

    return redirect(request.referrer or url_for("social.collection_detail", collection_id=collection_id))


@social_bp.route("/collections/<int:collection_id>/share", methods=["POST"])
@login_required
def collection_share(collection_id):
    """Share an entire collection."""
    collection = db.session.get(SocialCollection, collection_id)
    if not collection or collection.creator_id != current_user.id:
        abort(404)

    recipient_email = request.form.get("recipient_email", "").strip()
    recipient_name = request.form.get("recipient_name", "").strip()
    message = request.form.get("message", "").strip()

    if not recipient_email:
        flash("Please provide a recipient email.", "warning")
        return redirect(url_for("social.collection_detail", collection_id=collection_id))

    share = SocialShare(
        collection_id=collection_id,
        share_type="collection",
        sharer_id=current_user.id,
        sharer_name=current_user.username,
        sharer_email=current_user.email,
        recipient_email=recipient_email,
        recipient_name=recipient_name or None,
        message=message or None,
        share_token=SocialShare.generate_token(),
    )
    db.session.add(share)
    collection.share_count += 1
    db.session.commit()

    _send_collection_share_email(share, collection)

    flash(f"Collection shared with {recipient_name or recipient_email}!", "success")
    return redirect(url_for("social.collection_detail", collection_id=collection_id))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  REFERRALS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@social_bp.route("/referral")
@login_required
def referral_dashboard():
    """My referral dashboard."""
    referrals = Referral.query.filter_by(
        referrer_id=current_user.id,
    ).order_by(Referral.created_at.desc()).all()

    # Generate and persist a referral code if user doesn't have one yet
    existing_code = Referral.query.filter_by(referrer_id=current_user.id).first()
    if existing_code:
        my_code = existing_code.referral_code
    else:
        my_code = Referral.generate_code()
        # Persist so the link works immediately (even before sending an invite)
        placeholder = Referral(
            referrer_id=current_user.id,
            referred_email="pending",
            referral_code=my_code,
            status="invited",
        )
        db.session.add(placeholder)
        db.session.commit()

    return render_template("social/referral.html", referrals=referrals, my_code=my_code)


@social_bp.route("/referral/invite", methods=["POST"])
@login_required
def referral_invite():
    """Send a referral invitation."""
    referred_email = request.form.get("email", "").strip()
    if not referred_email:
        flash("Please provide an email address.", "warning")
        return redirect(url_for("social.referral_dashboard"))

    # Check if already referred
    existing = Referral.query.filter_by(
        referrer_id=current_user.id,
        referred_email=referred_email,
    ).first()
    if existing:
        flash("You've already invited this person.", "info")
        return redirect(url_for("social.referral_dashboard"))

    referral = Referral(
        referrer_id=current_user.id,
        referred_email=referred_email,
        referral_code=Referral.generate_code(),
    )
    db.session.add(referral)
    db.session.commit()

    _send_referral_email(referral)

    flash(f"Referral invitation sent to {referred_email}!", "success")
    return redirect(url_for("social.referral_dashboard"))


@social_bp.route("/r/<code>")
def referral_landing(code):
    """Referral landing page — registers attribution in session."""
    referral = Referral.query.filter_by(referral_code=code).first_or_404()
    session["referral_code"] = code
    session["referred_by"] = referral.referrer_id

    return render_template("social/referral_landing.html", referral=referral)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  SOCIAL ANALYTICS (Owner/Agent)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@social_bp.route("/analytics")
@login_required
def social_analytics():
    """Social activity analytics for owners and agents."""
    if not current_user.is_admin:
        abort(403)

    # Total shares
    total_shares = SocialShare.query.count()
    total_views = SocialShare.query.filter(SocialShare.viewed_at.isnot(None)).count()
    total_reactions = SocialReaction.query.count()
    total_collections = SocialCollection.query.count()
    total_referrals = Referral.query.count()

    # Most shared listings
    from sqlalchemy import func
    most_shared = db.session.query(
        Listing,
        func.count(SocialShare.id).label("share_count"),
    ).join(SocialShare, SocialShare.listing_id == Listing.id
    ).group_by(Listing.id
    ).order_by(func.count(SocialShare.id).desc()
    ).limit(10).all()

    # Recent shares
    recent_shares = SocialShare.query.order_by(
        SocialShare.created_at.desc()
    ).limit(20).all()

    return render_template(
        "social/analytics.html",
        total_shares=total_shares,
        total_views=total_views,
        total_reactions=total_reactions,
        total_collections=total_collections,
        total_referrals=total_referrals,
        most_shared=most_shared,
        recent_shares=recent_shares,
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  POINTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@social_bp.route("/points")
@login_required
def points_history():
    """View my points balance and history."""
    from app.services.points import get_balance
    balance = get_balance(current_user.id)
    account = UserPoints.query.filter_by(user_id=current_user.id).first()
    logs = UserPointLog.query.filter_by(
        user_id=current_user.id,
    ).order_by(UserPointLog.created_at.desc()).limit(50).all()

    return render_template("social/points.html",
                           balance=balance, account=account, logs=logs)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  LEADERBOARD
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@social_bp.route("/leaderboard")
@login_required
def leaderboard():
    """Monthly leaderboard: top sharers and referrers."""
    from sqlalchemy import func
    from datetime import timedelta

    month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Top sharers this month
    top_sharers = db.session.query(
        User,
        func.count(SocialShare.id).label("share_count"),
    ).join(SocialShare, SocialShare.sharer_id == User.id
    ).filter(SocialShare.created_at >= month_start
    ).group_by(User.id
    ).order_by(func.count(SocialShare.id).desc()
    ).limit(10).all()

    # Top referrers this month
    top_referrers = db.session.query(
        User,
        func.count(Referral.id).label("referral_count"),
    ).join(Referral, Referral.referrer_id == User.id
    ).filter(Referral.created_at >= month_start
    ).group_by(User.id
    ).order_by(func.count(Referral.id).desc()
    ).limit(10).all()

    return render_template("social/leaderboard.html",
                           top_sharers=top_sharers,
                           top_referrers=top_referrers,
                           month_start=month_start)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ADD A HOME (Friend-Listed)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@social_bp.route("/add-home", methods=["GET", "POST"])
@login_required
def add_home():
    """Submit a friend/neighbor's home as a listing tip."""
    if request.method == "POST":
        address = request.form.get("address", "").strip()
        city = request.form.get("city", "").strip()
        zip_code = request.form.get("zip_code", "").strip()
        price = request.form.get("price", type=int)
        bedrooms = request.form.get("bedrooms", type=int)
        bathrooms = request.form.get("bathrooms", type=float)
        sqft = request.form.get("sqft", type=int)
        description = request.form.get("description", "").strip()
        relationship = request.form.get("relationship", "friend")
        has_permission = request.form.get("has_permission") == "on"

        if not address or not zip_code:
            flash("Address and zip code are required.", "warning")
            return render_template("social/add_home.html")

        if not has_permission:
            flash("You must confirm you have permission to share this listing.", "warning")
            return render_template("social/add_home.html")

        # Handle photo uploads (max 5)
        import json as _json
        import os
        import uuid
        photos = []
        upload_dir = os.path.join(current_app.static_folder, "uploads")
        os.makedirs(upload_dir, exist_ok=True)

        uploaded_files = request.files.getlist("photos")
        for f in uploaded_files[:5]:
            if f and f.filename:
                ext = os.path.splitext(f.filename)[1].lower()
                if ext in (".jpg", ".jpeg", ".png", ".webp"):
                    safe_name = f"{uuid.uuid4().hex}{ext}"
                    f.save(os.path.join(upload_dir, safe_name))
                    photos.append(safe_name)

        from datetime import timedelta
        friend_listing = FriendListing(
            submitter_id=current_user.id,
            submitter_email=current_user.email,
            address=address,
            city=city or None,
            zip_code=zip_code,
            price=price,
            bedrooms=bedrooms,
            bathrooms=bathrooms,
            sqft=sqft,
            description=description or None,
            photos_json=_json.dumps(photos),
            relationship=relationship,
            has_permission=True,
            expires_at=datetime.now(timezone.utc) + timedelta(days=90),
        )
        db.session.add(friend_listing)
        db.session.commit()

        # Award points
        try:
            from app.services.points import award_points
            award_points(current_user.id, 5, "friend_listing", reference_id=friend_listing.id)
        except Exception:
            pass

        flash("Home submitted! It will appear as a Neighborhood Tip.", "success")
        return _site_redirect("social.friend_listings")

    return render_template("social/add_home.html")


@social_bp.route("/friend-listings")
def friend_listings():
    """Browse active friend-listed homes."""
    import json as _json
    site = getattr(g, "site", None)
    site_zips = []
    if site and site.get("zip_codes_json"):
        try:
            site_zips = _json.loads(site["zip_codes_json"])
        except (ValueError, TypeError):
            pass

    query = FriendListing.query.filter_by(status="active")
    if site_zips:
        query = query.filter(FriendListing.zip_code.in_(site_zips))
    listings = query.order_by(FriendListing.created_at.desc()).all()

    return render_template("social/friend_listings.html", friend_listings=listings)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  SOCIAL DIGEST (Owner trigger)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@social_bp.route("/send-digest", methods=["POST"])
@login_required
def send_digest():
    """Trigger weekly social digest emails (owner/master only)."""
    if not current_user.is_admin:
        abort(403)

    try:
        from app.services.social_digest import send_weekly_digests
        site = getattr(g, "site", None)
        site_key = site["site_key"] if site else "unknown"
        count = send_weekly_digests(site_key)
        flash(f"Social digest sent to {count} user(s).", "success")
    except Exception as exc:
        log.error(f"Digest send failed: {exc}")
        flash(f"Failed to send digest: {exc}", "danger")

    return redirect(request.referrer or url_for("social.social_analytics"))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  EMAIL HELPERS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _send_share_email(share, listing):
    """Send the share notification email."""
    try:
        share_url = _share_url(share.share_token)
        sharer = share.sharer_name or "Someone"

        msg = Message(
            subject=f"{sharer} shared a listing with you on HomeFinder!",
            recipients=[share.recipient_email],
            html=render_template(
                "email/share_notification.html",
                share=share,
                listing=listing,
                share_url=share_url,
                sharer=sharer,
            ),
        )
        mail.send(msg)
    except Exception as exc:
        log.warning(f"Failed to send share email: {exc}")


def _send_reaction_email(share, reaction_type):
    """Notify the sharer that someone reacted."""
    if not share.sharer_email:
        return
    try:
        reactor = share.recipient_name or share.recipient_email
        reaction_label = dict((r[0], r[1]) for r in REACTION_TYPES).get(reaction_type, reaction_type)

        msg = Message(
            subject=f"{reactor} reacted to your shared listing!",
            recipients=[share.sharer_email],
            html=render_template(
                "email/reaction_notification.html",
                share=share,
                reactor=reactor,
                reaction_label=reaction_label,
            ),
        )
        mail.send(msg)
    except Exception as exc:
        log.warning(f"Failed to send reaction email: {exc}")


def _send_collection_share_email(share, collection):
    """Send collection share notification email."""
    try:
        collection_url = url_for("social.collection_public", token=collection.share_token, _external=True)
        sharer = share.sharer_name or "Someone"

        msg = Message(
            subject=f"{sharer} shared a collection with you on HomeFinder!",
            recipients=[share.recipient_email],
            html=render_template(
                "email/collection_share_notification.html",
                share=share,
                collection=collection,
                collection_url=collection_url,
                sharer=sharer,
            ),
        )
        mail.send(msg)
    except Exception as exc:
        log.warning(f"Failed to send collection share email: {exc}")


def _send_referral_email(referral):
    """Send referral invitation email."""
    try:
        referral_url = url_for("social.referral_landing", code=referral.referral_code, _external=True)
        referrer = referral.referrer

        msg = Message(
            subject=f"{referrer.username} invited you to HomeFinder!",
            recipients=[referral.referred_email],
            html=render_template(
                "email/referral_invitation.html",
                referral=referral,
                referrer=referrer,
                referral_url=referral_url,
            ),
        )
        mail.send(msg)
    except Exception as exc:
        log.warning(f"Failed to send referral email: {exc}")
