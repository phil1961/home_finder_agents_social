# ─────────────────────────────────────────────
# File: app/routes/agent_routes.py
# App Version: 2026.03.14 | File Version: 1.5.0
# Last Modified: 2026-03-14
# ─────────────────────────────────────────────
"""
app/routes/agent_routes.py — Agent management routes.
"""
from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user

from app.models import db, Listing, User
from app.routes.dashboard_helpers import dashboard_bp, _site_redirect
from app.utils import site_url_external as _site_url_external


@dashboard_bp.route("/agent/dashboard")
@login_required
def agent_dashboard():
    """Agent home: client list + branding settings."""
    if not current_user.is_agent:
        flash("Access denied.", "danger")
        return _site_redirect("dashboard.index")

    profile = current_user.agent_profile
    clients = (
        User.query
        .filter_by(agent_id=profile.id)
        .order_by(User.created_at.desc())
        .all()
    ) if profile else []

    # Attach favorite count per client for the overview table
    from app.models import UserFlag
    favorite_counts = {}
    for client in clients:
        favorite_counts[client.id] = UserFlag.query.filter_by(
            user_id=client.id, flag="favorite"
        ).count()

    # Load agent notes for all clients
    from app.models import AgentClientNote, ListingNote
    client_notes = {}
    if profile:
        for note in AgentClientNote.query.filter_by(agent_id=profile.id).all():
            client_notes[note.client_id] = note

    # Load listing notes for all clients, grouped by client_id
    # Only load notes that have actual content (text or a checked box)
    client_listing_notes = {}
    if clients:
        client_ids = [c.id for c in clients]
        all_listing_notes = (
            ListingNote.query
            .filter(ListingNote.user_id.in_(client_ids))
            .filter(
                db.or_(
                    ListingNote.note_text != "",
                    ListingNote.note_text.isnot(None),
                    ListingNote.visited == True,
                    ListingNote.scheduled_visit == True,
                    ListingNote.made_offer == True,
                    ListingNote.not_interested == True,
                )
            )
            .all()
        )
        # Attach listing objects
        listing_ids = [n.listing_id for n in all_listing_notes]
        listings_by_id = {l.id: l for l in Listing.query.filter(Listing.id.in_(listing_ids)).all()} if listing_ids else {}
        for ln in all_listing_notes:
            ln._listing = listings_by_id.get(ln.listing_id)
            client_listing_notes.setdefault(ln.user_id, []).append(ln)

    # Pending friend listings from this agent's clients
    pending_friend_listings = []
    if profile and clients:
        from app.models_social import FriendListing
        client_ids = [c.id for c in clients]
        pending_friend_listings = FriendListing.query.filter(
            FriendListing.submitter_id.in_(client_ids),
            FriendListing.status == "active",
        ).order_by(FriendListing.created_at.desc()).all()

    return render_template(
        "dashboard/agent_dashboard.html",
        profile=profile,
        clients=clients,
        favorite_counts=favorite_counts,
        client_notes=client_notes,
        client_listing_notes=client_listing_notes,
        pending_friend_listings=pending_friend_listings,
        user=current_user,
    )


@dashboard_bp.route("/agent/clients/<int:client_id>/notes", methods=["POST"])
@login_required
def agent_client_notes(client_id):
    """Save agent notes and checkboxes for a client. Returns JSON."""
    if not current_user.is_admin:
        return jsonify({"error": "Access denied"}), 403

    profile = current_user.agent_profile
    if not profile:
        return jsonify({"error": "No agent profile"}), 403

    from app.models import AgentClientNote
    # Verify this client belongs to this agent (owner can access any client)
    if current_user.is_owner:
        client = User.query.get(client_id)
    else:
        client = User.query.filter_by(id=client_id, agent_id=profile.id).first()
    if not client:
        return jsonify({"error": "Client not found"}), 404

    note = AgentClientNote.for_agent_client(profile.id, client_id)
    note.notes            = request.form.get("notes", "").strip()
    note.pre_approved     = request.form.get("pre_approved") == "on"
    note.signed_agreement = request.form.get("signed_agreement") == "on"
    note.tour_scheduled   = request.form.get("tour_scheduled") == "on"
    note.offer_submitted  = request.form.get("offer_submitted") == "on"
    note.active_searching = request.form.get("active_searching") == "on"

    try:
        db.session.commit()
        return jsonify({"ok": True})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@dashboard_bp.route("/agent/clients/<int:client_id>/prefs", methods=["GET", "POST"])
@login_required
def agent_client_prefs(client_id):
    """Agent views and sets scoring preferences for a specific client."""
    if not current_user.is_agent:
        flash("Access denied.", "danger")
        return _site_redirect("dashboard.index")

    profile = current_user.agent_profile
    client = db.session.get(User, client_id)

    if not client or client.agent_id != profile.id:
        flash("Client not found.", "danger")
        return _site_redirect("dashboard.agent_dashboard")

    if request.method == "POST":
        try:
            imp_keys = [k for k in User.DEFAULT_PREFS if k.startswith("imp_")]
            prefs = {
                "min_price": int(request.form.get("min_price", 200000)),
                "max_price": int(request.form.get("max_price", 600000)),
                "min_beds": int(request.form.get("min_beds", 4)),
                "min_baths": float(request.form.get("min_baths", 3)),
                "must_have_garage": request.form.get("must_have_garage") == "on",
                "must_have_porch": request.form.get("must_have_porch") == "on",
                "must_have_patio": request.form.get("must_have_patio") == "on",
                "great_deal_threshold": int(request.form.get("great_deal_threshold", 75)),
                "avoid_areas": [
                    a.strip() for a in request.form.get("avoid_areas", "").split(",")
                    if a.strip()
                ],
            }
            for k in imp_keys:
                prefs[k] = int(request.form.get(k, User.DEFAULT_PREFS.get(k, 5)))

            client.set_prefs(prefs)
            db.session.commit()
            flash(f"Preferences saved for {client.username}.", "success")
        except (ValueError, TypeError) as e:
            flash(f"Invalid input: {e}", "danger")

        return _site_redirect("dashboard.agent_client_prefs", client_id=client_id)

    prefs = client.get_prefs()
    return render_template(
        "dashboard/agent_client_prefs.html",
        client=client,
        prefs=prefs,
        prefs_defaults=User.DEFAULT_PREFS,
        user=current_user,
    )


@dashboard_bp.route("/agent/clients/create", methods=["POST"])
@login_required
def agent_create_client():
    """Agent creates a client account. Sends welcome email with credentials."""
    import re
    import secrets
    import string
    from flask import current_app
    from flask_mail import Message
    from app import mail

    if not current_user.is_agent:
        flash("Access denied.", "danger")
        return _site_redirect("dashboard.index")

    profile = current_user.agent_profile
    if not profile:
        flash("No agent profile found. Please complete agent signup first.", "danger")
        return _site_redirect("dashboard.index")

    client_name = request.form.get("client_name", "").strip()
    client_email = request.form.get("client_email", "").strip().lower()
    intro_message = request.form.get("intro_message", "").strip()

    errors = []
    if not client_name:
        errors.append("Client name is required.")
    if not client_email or "@" not in client_email:
        errors.append("A valid email address is required.")
    if User.query.filter_by(email=client_email).first():
        errors.append(f"{client_email} already has an account.")

    if errors:
        for e in errors:
            flash(e, "danger")
        return _site_redirect("dashboard.agent_dashboard")

    # Auto-generate a unique username from the email prefix
    base = re.sub(r'[^a-z0-9]', '', client_email.split('@')[0].lower())
    if len(base) < 3:
        base = base + "user"
    username = base
    counter = 1
    while User.query.filter_by(username=username).first():
        username = f"{base}{counter}"
        counter += 1

    # Generate a random password
    chars = string.ascii_letters + string.digits
    temp_password = ''.join(secrets.choice(chars) for _ in range(12))

    # Create the client user — pre-verified, linked to this agent
    client = User(
        username=username,
        email=client_email,
        role="user",
        is_verified=True,
        agent_id=profile.id,
    )
    client.set_password(temp_password)
    db.session.add(client)
    db.session.commit()

    # Send welcome email — include site context so link lands in correct market
    try:
        from flask import g
        site = getattr(g, "site", None) or {}
        login_url = _site_url_external("auth.login", username=username)
        site_name = site.get("display_name", "HomeFinder")
        msg = Message(
            subject=f"Your HomeFinder Account — {profile.full_name}",
            recipients=[client_email],
            html=render_template(
                "auth/client_welcome_email_body.html",
                client_name=client_name,
                username=username,
                temp_password=temp_password,
                agent=profile,
                intro_message=intro_message,
                login_url=login_url,
                site_name=site_name,
            ),
        )
        mail.send(msg)
        flash(f"Account created for {client_name} and welcome email sent to {client_email}.", "success")
    except Exception as exc:
        current_app.logger.error(f"Client welcome email failed: {exc}")
        flash(
            f"Account created for {client_name} (username: {username}, password: {temp_password}), "
            f"but the welcome email failed. Please share credentials manually.",
            "warning",
        )

    return _site_redirect("dashboard.agent_dashboard")


@dashboard_bp.route("/agent/clients/resend-welcome", methods=["POST"])
@login_required
def agent_resend_welcome():
    """Resend welcome email to an existing client with a new temp password."""
    import secrets
    import string
    from flask import current_app, g
    from flask_mail import Message
    from app import mail

    if not current_user.is_agent:
        return jsonify({"ok": False, "error": "Access denied."}), 403

    profile = current_user.agent_profile
    if not profile:
        return jsonify({"ok": False, "error": "No agent profile."}), 403

    data = request.get_json(silent=True) or {}
    client_id = data.get("client_id")
    if not client_id:
        return jsonify({"ok": False, "error": "client_id required."}), 400

    client = User.query.filter_by(id=client_id, agent_id=profile.id).first()
    if not client:
        return jsonify({"ok": False, "error": "Client not found."}), 404

    # Generate a new temp password
    chars = string.ascii_letters + string.digits
    temp_password = ''.join(secrets.choice(chars) for _ in range(12))
    client.set_password(temp_password)
    db.session.commit()

    try:
        site = getattr(g, "site", None) or {}
        login_url = _site_url_external("auth.login", username=client.username)
        site_name = site.get("display_name", "HomeFinder")
        msg = Message(
            subject=f"Your HomeFinder Account — {profile.full_name}",
            recipients=[client.email],
            html=render_template(
                "auth/client_welcome_email_body.html",
                client_name=client.username,
                username=client.username,
                temp_password=temp_password,
                agent=profile,
                intro_message="",
                login_url=login_url,
                site_name=site_name,
            ),
        )
        mail.send(msg)
        return jsonify({"ok": True, "message": f"Welcome email resent to {client.email}."})
    except Exception as exc:
        current_app.logger.error(f"Resend welcome email failed: {exc}")
        return jsonify({
            "ok": False,
            "error": f"Email failed. New password: {temp_password} — share manually.",
        }), 500


# ── Prompt editor — agent (per-agent override) ───────────────────
@dashboard_bp.route("/agent/prompts", methods=["GET", "POST"])
@login_required
def agent_prompts():
    """Agent edits their own prompt overrides."""
    if not current_user.is_admin:
        flash("Access denied.", "danger")
        return _site_redirect("dashboard.index")

    profile = current_user.agent_profile
    if not profile:
        flash("No agent profile found.", "danger")
        return _site_redirect("dashboard.index")

    from app.models import PromptOverride
    from config import DEFAULT_PROMPTS

    if request.method == "POST":
        for ptype in ("deal", "portfolio", "preferences"):
            text = request.form.get(f"prompt_{ptype}", "").strip()
            if text:
                PromptOverride.upsert(ptype, text, agent_id=profile.id)
            else:
                PromptOverride.delete(ptype, agent_id=profile.id)
        db.session.commit()
        flash("Your prompt overrides saved.", "success")
        return _site_redirect("dashboard.agent_prompts")

    overrides = {}
    effective = {}
    for ptype in ("deal", "portfolio", "preferences"):
        row = PromptOverride.get_for_edit(ptype, agent_id=profile.id)
        overrides[ptype] = row.system_prompt if row else ""
        effective[ptype] = PromptOverride.resolve(ptype, profile.id) or DEFAULT_PROMPTS[ptype]

    return render_template("dashboard/agent_prompts.html",
                           overrides=overrides, effective=effective,
                           defaults=DEFAULT_PROMPTS, profile=profile,
                           user=current_user)


@dashboard_bp.route("/agent/branding", methods=["POST"])
@login_required
def agent_branding():
    """Save agent branding settings."""
    if not current_user.is_agent:
        flash("Access denied.", "danger")
        return _site_redirect("dashboard.index")

    profile = current_user.agent_profile
    if not profile:
        flash("No agent profile found. Please complete agent signup first.", "danger")
        return _site_redirect("dashboard.index")

    color = request.form.get("brand_color", "#2563eb").strip()
    logo_url = request.form.get("brand_logo_url", "").strip() or None
    brand_icon = request.form.get("brand_icon", "").strip() or None
    tagline = request.form.get("brand_tagline", "").strip() or None
    tagline_style = request.form.get("brand_tagline_style", "plain").strip()

    # Validate
    import re
    if not re.match(r'^#[0-9A-Fa-f]{6}$', color):
        color = "#2563eb"
    valid_styles = {"plain", "italic", "bold", "caps", "badge", "elegant"}
    if tagline_style not in valid_styles:
        tagline_style = "plain"
    # Validate icon — emoji chars are 1-8 bytes of Unicode, no HTML allowed
    if brand_icon:
        import html
        brand_icon = html.escape(brand_icon.strip())[:10] or None

    profile.brand_color = color
    profile.brand_logo_url = logo_url
    profile.brand_icon = brand_icon
    profile.brand_tagline = tagline
    profile.brand_tagline_style = tagline_style
    db.session.commit()
    flash("Branding updated.", "success")
    return _site_redirect("dashboard.agent_dashboard")


# ── Friend Listing Review / Approve ─────────────────────────────

@dashboard_bp.route("/agent/friend-listing/<int:fl_id>/review", methods=["GET", "POST"])
@login_required
def agent_review_friend_listing(fl_id):
    """Agent reviews and optionally edits a friend-listed home before approval."""
    if not current_user.is_agent:
        flash("Access denied.", "danger")
        return _site_redirect("dashboard.index")

    profile = current_user.agent_profile
    from app.models_social import FriendListing
    fl = db.session.get(FriendListing, fl_id)
    if not fl:
        flash("Listing not found.", "danger")
        return _site_redirect("dashboard.agent_dashboard")

    # Verify submitter is this agent's client (or owner can review any)
    submitter = db.session.get(User, fl.submitter_id) if fl.submitter_id else None
    if not current_user.is_owner:
        if not submitter or submitter.agent_id != profile.id:
            flash("You can only review listings from your own clients.", "danger")
            return _site_redirect("dashboard.agent_dashboard")

    if request.method == "POST":
        # Save edits to the FriendListing fields
        fl.address = request.form.get("address", fl.address).strip()
        fl.city = request.form.get("city", "").strip() or fl.city
        fl.zip_code = request.form.get("zip_code", fl.zip_code).strip()
        fl.price = request.form.get("price", type=int) or fl.price
        fl.bedrooms = request.form.get("bedrooms", type=int) if request.form.get("bedrooms") else fl.bedrooms
        fl.bathrooms = request.form.get("bathrooms", type=float) if request.form.get("bathrooms") else fl.bathrooms
        fl.sqft = request.form.get("sqft", type=int) if request.form.get("sqft") else fl.sqft
        fl.description = request.form.get("description", "").strip() or fl.description
        db.session.commit()
        flash("Listing details updated.", "success")
        return _site_redirect("dashboard.agent_review_friend_listing", fl_id=fl.id)

    return render_template("dashboard/agent_review_friend_listing.html",
                           fl=fl, submitter=submitter, profile=profile,
                           user=current_user)


@dashboard_bp.route("/agent/friend-listing/<int:fl_id>/approve", methods=["POST"])
@login_required
def agent_approve_friend_listing(fl_id):
    """Approve a friend listing and create a real Listing record."""
    from datetime import datetime, timezone
    import json as _json

    if not current_user.is_agent:
        flash("Access denied.", "danger")
        return _site_redirect("dashboard.index")

    profile = current_user.agent_profile
    from app.models_social import FriendListing
    fl = db.session.get(FriendListing, fl_id)
    if not fl or fl.status != "active":
        flash("Listing not found or already processed.", "danger")
        return _site_redirect("dashboard.agent_dashboard")

    # Verify submitter is this agent's client
    submitter = db.session.get(User, fl.submitter_id) if fl.submitter_id else None
    if not current_user.is_owner:
        if not submitter or submitter.agent_id != profile.id:
            flash("Access denied.", "danger")
            return _site_redirect("dashboard.agent_dashboard")

    # Check for duplicate source_id
    source_id = f"community_{fl.id}"
    existing = Listing.query.filter_by(source_id=source_id).first()
    if existing:
        flash("This listing has already been approved.", "info")
        return _site_redirect("dashboard.agent_dashboard")

    # Convert uploaded photo filenames to URL paths
    photos = _json.loads(fl.photos_json or "[]")
    photo_urls = [f"/static/uploads/{fname}" for fname in photos]

    # Resolve area_name from zip code using site target areas
    area_name = None
    try:
        from app.routes.dashboard_helpers import _get_site_target_areas
        target_areas = _get_site_target_areas()
        for area, zips in target_areas.items():
            if fl.zip_code in zips:
                area_name = area
                break
    except Exception:
        pass

    listing = Listing(
        source="community",
        source_id=source_id,
        status="active",
        address=fl.address,
        city=fl.city,
        zip_code=fl.zip_code,
        area_name=area_name,
        price=fl.price,
        beds=fl.bedrooms,
        baths=fl.bathrooms,
        sqft=fl.sqft,
        description=fl.description,
        photo_urls_json=_json.dumps(photo_urls) if photo_urls else None,
        details_fetched=True,  # no API enrichment needed
        # Agent-provided enrichment from the approve form
        lot_sqft=request.form.get("lot_sqft", type=int),
        year_built=request.form.get("year_built", type=int),
        latitude=request.form.get("latitude", type=float),
        longitude=request.form.get("longitude", type=float),
        has_garage=request.form.get("has_garage") == "on",
        has_porch=request.form.get("has_porch") == "on",
        has_patio=request.form.get("has_patio") == "on",
        is_single_story=request.form.get("is_single_story") == "on",
        has_community_pool=request.form.get("has_community_pool") == "on",
        hoa_monthly=request.form.get("hoa_monthly", type=float),
        property_tax_annual=request.form.get("property_tax_annual", type=float),
        stories=request.form.get("stories", type=int),
    )
    db.session.add(listing)
    db.session.flush()  # get listing.id

    # Score the listing
    try:
        from pipeline import _score_listing
        _score_listing(listing)
    except Exception as exc:
        from flask import current_app
        current_app.logger.warning(f"Failed to score community listing {listing.id}: {exc}")

    # Update FriendListing
    fl.status = "approved"
    fl.approved_by_agent_id = profile.id
    fl.approved_at = datetime.now(timezone.utc)
    fl.listing_id = listing.id
    db.session.commit()

    # Award points for approving a community listing
    try:
        from app.services.points import award_points
        award_points(current_user.id, 3, "listing_approved", reference_id=listing.id)
    except Exception:
        pass

    flash(f"Listing approved and live! \"{fl.address}\" is now in the main grid with a deal score.", "success")
    return _site_redirect("dashboard.agent_dashboard")


@dashboard_bp.route("/agent/friend-listing/<int:fl_id>/reject", methods=["POST"])
@login_required
def agent_reject_friend_listing(fl_id):
    """Reject a friend listing."""
    if not current_user.is_agent:
        flash("Access denied.", "danger")
        return _site_redirect("dashboard.index")

    profile = current_user.agent_profile
    from app.models_social import FriendListing
    fl = db.session.get(FriendListing, fl_id)
    if not fl or fl.status != "active":
        flash("Listing not found or already processed.", "danger")
        return _site_redirect("dashboard.agent_dashboard")

    submitter = db.session.get(User, fl.submitter_id) if fl.submitter_id else None
    if not current_user.is_owner:
        if not submitter or submitter.agent_id != profile.id:
            flash("Access denied.", "danger")
            return _site_redirect("dashboard.agent_dashboard")

    fl.status = "rejected"
    fl.rejection_reason = request.form.get("reason", "").strip() or None
    db.session.commit()

    flash(f"Listing \"{fl.address}\" has been rejected.", "info")
    return _site_redirect("dashboard.agent_dashboard")


# ── Agent Direct Listing ────────────────────────────────────────

@dashboard_bp.route("/agent/add-listing", methods=["GET", "POST"])
@login_required
def agent_add_listing():
    """Agent creates a listing directly — no community referral needed."""
    if not current_user.is_agent:
        flash("Access denied.", "danger")
        return _site_redirect("dashboard.index")

    profile = current_user.agent_profile
    if not profile:
        flash("No agent profile found.", "danger")
        return _site_redirect("dashboard.index")

    if request.method == "POST":
        from datetime import datetime, timezone
        import json as _json
        import os
        import uuid
        from flask import current_app

        address = request.form.get("address", "").strip()
        zip_code = request.form.get("zip_code", "").strip()

        if not address or not zip_code:
            flash("Address and zip code are required.", "warning")
            return render_template("dashboard/agent_add_listing.html",
                                   profile=profile, user=current_user)

        # Handle photo uploads (max 5)
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
                    photos.append(f"/static/uploads/{safe_name}")

        # Generate unique source_id
        source_id = f"agent_{profile.id}_{uuid.uuid4().hex[:8]}"

        # Resolve area_name from zip code
        area_name = None
        try:
            from app.routes.dashboard_helpers import _get_site_target_areas
            target_areas = _get_site_target_areas()
            for area, zips in target_areas.items():
                if zip_code in zips:
                    area_name = area
                    break
        except Exception:
            pass

        listing = Listing(
            source="agent",
            source_id=source_id,
            status="active",
            address=address,
            city=request.form.get("city", "").strip() or None,
            zip_code=zip_code,
            area_name=area_name,
            price=request.form.get("price", type=int),
            beds=request.form.get("bedrooms", type=int),
            baths=request.form.get("bathrooms", type=float),
            sqft=request.form.get("sqft", type=int),
            lot_sqft=request.form.get("lot_sqft", type=int),
            year_built=request.form.get("year_built", type=int),
            latitude=request.form.get("latitude", type=float),
            longitude=request.form.get("longitude", type=float),
            description=request.form.get("description", "").strip() or None,
            photo_urls_json=_json.dumps(photos) if photos else None,
            details_fetched=True,
            has_garage=request.form.get("has_garage") == "on",
            has_porch=request.form.get("has_porch") == "on",
            has_patio=request.form.get("has_patio") == "on",
            is_single_story=request.form.get("is_single_story") == "on",
            has_community_pool=request.form.get("has_community_pool") == "on",
            hoa_monthly=request.form.get("hoa_monthly", type=float),
            property_tax_annual=request.form.get("property_tax_annual", type=float),
            stories=request.form.get("stories", type=int),
        )
        db.session.add(listing)
        db.session.flush()

        # Score it
        try:
            from pipeline import _score_listing
            _score_listing(listing)
        except Exception as exc:
            current_app.logger.warning(f"Failed to score agent listing {listing.id}: {exc}")

        db.session.commit()

        # Award points for creating a listing
        try:
            from app.services.points import award_points
            award_points(current_user.id, 5, "listing_created", reference_id=listing.id)
        except Exception:
            pass

        flash(f"Listing \"{address}\" created and scored!", "success")
        return _site_redirect("dashboard.listing_detail", listing_id=listing.id)

    return render_template("dashboard/agent_add_listing.html",
                           profile=profile, user=current_user)
