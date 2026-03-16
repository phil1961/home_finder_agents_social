# ─────────────────────────────────────────────
# File: app/routes/auth.py
# App Version: 2026.03.14 | File Version: 1.8.0
# Last Modified: 2026-03-14
# ─────────────────────────────────────────────
"""Authentication routes: register, login, logout, email verification."""
from datetime import datetime, timezone

from flask import (
    Blueprint, render_template, redirect, url_for, flash, request, current_app, g, session as flask_session
)
from flask_login import login_user, logout_user, login_required, current_user
from flask_mail import Message
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature

from app.models import db, User, AgentProfile
from app import mail
from app.utils import site_redirect as _site_redirect, site_url_external as _site_url_external, site_url as _site_url

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


# ── Token helpers ────────────────────────────────────────────────

def _get_serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"])


def generate_verification_token(email):
    s = _get_serializer()
    return s.dumps(email, salt="email-verify")


def confirm_verification_token(token, max_age=None):
    s = _get_serializer()
    if max_age is None:
        max_age = current_app.config.get("VERIFICATION_TOKEN_MAX_AGE", 3600)
    return s.loads(token, salt="email-verify", max_age=max_age)


def generate_reset_token(email):
    s = _get_serializer()
    return s.dumps(email, salt="password-reset")


def confirm_reset_token(token, max_age=3600):
    s = _get_serializer()
    return s.loads(token, salt="password-reset", max_age=max_age)


def _send_verification_email(user):
    token = generate_verification_token(user.email)
    verify_url = _site_url_external("auth.verify_email", token=token)
    watch_url  = _site_url_external("dashboard.watch_manage")
    msg = Message(
        subject="HomeFinder – Verify Your Email",
        recipients=[user.email],
        html=render_template("auth/verify_email_body.html",
                             user=user, verify_url=verify_url,
                             watch_url=watch_url),
    )
    mail.send(msg)


def _send_password_reset_email(user):
    token = generate_reset_token(user.email)
    reset_url = _site_url_external("auth.reset_password", token=token)
    msg = Message(
        subject="HomeFinder – Reset Your Password",
        recipients=[user.email],
        html=render_template("auth/reset_email_body.html",
                             user=user, reset_url=reset_url),
    )
    mail.send(msg)


def _send_welcome_email(user):
    """Send a welcome email after the user verifies their account."""
    from flask import g
    site = getattr(g, "site", None) or {}
    site_name = site.get("display_name", "HomeFinder")
    dashboard_url = _site_url_external("dashboard.index")
    msg = Message(
        subject=f"Welcome to HomeFinder – {site_name}",
        recipients=[user.email],
        html=render_template("auth/welcome_email_body.html",
                             user=user, dashboard_url=dashboard_url,
                             site_name=site_name),
    )
    mail.send(msg)


# ── Register ─────────────────────────────────────────────────────

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return _site_redirect("dashboard.index")

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        # Validation
        errors = []
        if not username or len(username) < 3:
            errors.append("Username must be at least 3 characters.")
        if not email or "@" not in email:
            errors.append("A valid email address is required.")
        if len(password) < 8:
            errors.append("Password must be at least 8 characters.")
        if password != confirm:
            errors.append("Passwords do not match.")
        if User.query.filter_by(email=email).first():
            errors.append("An account with that email already exists.")
        if User.query.filter_by(username=username).first():
            errors.append("That username is taken.")

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("auth/register.html",
                                   username=username, email=email)

        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        # Link any guest street watches to the new account
        try:
            from app.services.street_watch import link_watches_to_user
            link_watches_to_user(email, user.id)
        except Exception:
            pass  # non-critical

        # Close referral loop — attribute registration to referrer
        try:
            ref_code = flask_session.get("referral_code")
            if ref_code:
                from app.models_social import Referral
                referral = Referral.query.filter_by(referral_code=ref_code).first()
                if referral and not referral.referred_user_id:
                    referral.referred_user_id = user.id
                    referral.status = "registered"
                    referral.registered_at = datetime.now(timezone.utc)
                    db.session.commit()
                    # Award referrer points
                    try:
                        from app.services.points import award_points
                        award_points(referral.referrer_id, 10, "referral_registered", reference_id=referral.id)
                    except Exception:
                        pass
                flask_session.pop("referral_code", None)
                flask_session.pop("referred_by", None)
        except Exception:
            pass  # never block registration

        # Send verification email
        try:
            _send_verification_email(user)
            flash("Account created! Check your email to verify your address.", "success")
        except Exception as exc:
            current_app.logger.error(f"Mail send failed: {exc}")
            flash("Account created, but we couldn't send the verification email. "
                  "You can request a new one from the login page.", "warning")

        return _site_redirect("auth.login")

    return render_template("auth/register.html")


# ── Email verification ───────────────────────────────────────────

@auth_bp.route("/verify/<token>")
def verify_email(token):
    try:
        email = confirm_verification_token(token)
    except SignatureExpired:
        flash("That verification link has expired. Please request a new one.", "warning")
        return _site_redirect("auth.resend_verification")
    except BadSignature:
        flash("Invalid verification link.", "danger")
        return _site_redirect("auth.login")

    user = User.query.filter_by(email=email).first()
    if user is None:
        flash("Account not found.", "danger")
        return _site_redirect("auth.register")

    if user.is_verified:
        flash("Your email is already verified. Please sign in.", "info")
    else:
        user.is_verified = True
        db.session.commit()
        flash("Email verified! You can now sign in.", "success")
        # Send welcome email
        try:
            _send_welcome_email(user)
        except Exception as e:
            current_app.logger.error(f"Welcome email failed: {e}")

    return _site_redirect("auth.login")


@auth_bp.route("/resend-verification", methods=["GET", "POST"])
def resend_verification():
    if current_user.is_authenticated:
        return _site_redirect("dashboard.index")

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        user = User.query.filter_by(email=email).first()
        # Always show the same message to prevent email enumeration
        if user and not user.is_verified:
            try:
                _send_verification_email(user)
            except Exception as exc:
                current_app.logger.error(f"Mail send failed: {exc}")
        flash("If that email is in our system, a new verification link has been sent.", "info")
        return _site_redirect("auth.login")

    return render_template("auth/resend_verification.html")


# ── Login / Logout ───────────────────────────────────────────────

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return _site_redirect("dashboard.index")

    if request.method == "POST":
        login_id = request.form.get("login_id", "").strip()
        password = request.form.get("password", "")
        remember = request.form.get("remember") == "on"

        # Allow login by email OR username
        # When multiple accounts share the same email, prefer the highest role
        _role_priority = {"master": 0, "owner": 1, "agent": 2, "principal": 3, "client": 4, "user": 5}
        candidates = User.query.filter(
            (User.email == login_id.lower()) | (User.username == login_id)
        ).all()
        candidates.sort(key=lambda u: _role_priority.get(u.role, 99))
        user = candidates[0] if candidates else None

        if user is None or not user.check_password(password):
            flash("Invalid credentials.", "danger")
            return render_template("auth/login.html", login_id=login_id)

        if not user.is_verified:
            flash("Please verify your email before signing in. "
                  '<a href="' + _site_url("auth.resend_verification") +
                  '">Resend verification email</a>', "warning")
            return render_template("auth/login.html", login_id=login_id)

        if user.is_suspended:
            reason = f" Reason: {user.suspended_reason}" if user.suspended_reason else ""
            flash(f"Your account has been suspended.{reason} "
                  "Please contact the site owner.", "danger")
            return render_template("auth/login.html", login_id=login_id)

        # Check if agent is pending approval
        if user.is_agent and user.agent_profile and not user.agent_profile.is_approved:
            if user.agent_profile.status == "pending":
                flash("Your agent account is awaiting approval from the site owner. "
                      "You'll receive an email once approved.", "info")
                return render_template("auth/login.html", login_id=login_id)
            elif user.agent_profile.status == "suspended":
                flash("Your agent account has been suspended. "
                      "Please contact the site owner.", "danger")
                return render_template("auth/login.html", login_id=login_id)

        user.last_login = datetime.now(timezone.utc)
        db.session.commit()
        login_user(user, remember=remember)
        flask_session["_site_key"] = g.site["site_key"]

        next_page = request.args.get("next")
        flash(f"Welcome back, {user.username}!", "success")
        return _site_redirect("dashboard.index") if not next_page else redirect(next_page)

    return render_template("auth/login.html",
                           login_id=request.args.get("username", ""))


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You've been signed out.", "info")
    return _site_redirect("auth.login")


@auth_bp.route("/close-account", methods=["GET", "POST"])
@login_required
def close_account():
    """Close the user's account. Renames credentials so the email is freed up."""
    if request.method == "POST":
        password = request.form.get("password", "")
        confirm_text = request.form.get("confirm_text", "").strip()

        if not current_user.check_password(password):
            flash("Incorrect password.", "danger")
            return render_template("auth/close_account.html")

        if confirm_text.upper() != "CLOSE MY ACCOUNT":
            flash('Please type "CLOSE MY ACCOUNT" to confirm.', "danger")
            return render_template("auth/close_account.html")

        # Rename email and username to free them for re-registration
        uid = current_user.id
        original_username = current_user.username
        current_user.username = f"closed_{uid}_{current_user.username}"
        current_user.email = f"closed_{uid}_{current_user.email}"
        current_user.is_verified = False
        # Scramble password so the account can never be logged into
        current_user.password_hash = "ACCOUNT_CLOSED"
        db.session.commit()

        logout_user()
        flash(f"Your account has been closed, {original_username}. "
              "You're welcome back anytime — just register with the same email.",
              "info")
        return _site_redirect("auth.login")

    return render_template("auth/close_account.html")


# ── Password reset ───────────────────────────────────────────────

@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if current_user.is_authenticated:
        return _site_redirect("dashboard.index")

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        user = User.query.filter_by(email=email).first()
        if user:
            try:
                _send_password_reset_email(user)
            except Exception as exc:
                current_app.logger.error(f"Mail send failed: {exc}")
        flash("If that email is registered, a password-reset link has been sent.", "info")
        return _site_redirect("auth.login")

    return render_template("auth/forgot_password.html")


@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    try:
        email = confirm_reset_token(token)
    except (SignatureExpired, BadSignature):
        flash("Invalid or expired reset link.", "danger")
        return _site_redirect("auth.forgot_password")

    user = User.query.filter_by(email=email).first()
    if user is None:
        flash("Account not found.", "danger")
        return _site_redirect("auth.register")

    if request.method == "POST":
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        if len(password) < 8:
            flash("Password must be at least 8 characters.", "danger")
        elif password != confirm:
            flash("Passwords do not match.", "danger")
        else:
            user.set_password(password)
            db.session.commit()
            flash("Password updated! Please sign in.", "success")
            return _site_redirect("auth.login")

    return render_template("auth/reset_password.html")


# ── Agent signup ────────────────────────────────────────────────

@auth_bp.route("/agent-signup", methods=["GET", "POST"])
def agent_signup():
    """Registration page for real estate agents / operators."""
    if current_user.is_authenticated:
        return _site_redirect("dashboard.index")

    if request.method == "POST":
        # Account fields
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        # Agent profile fields
        full_name = request.form.get("full_name", "").strip()
        license_number = request.form.get("license_number", "").strip()
        brokerage = request.form.get("brokerage", "").strip()
        phone = request.form.get("phone", "").strip()
        bio = request.form.get("bio", "").strip()
        service_areas = request.form.get("service_areas", "").strip()

        # Validation
        errors = []
        if not username or len(username) < 3:
            errors.append("Username must be at least 3 characters.")
        if not email or "@" not in email:
            errors.append("A valid email address is required.")
        if len(password) < 8:
            errors.append("Password must be at least 8 characters.")
        if password != confirm:
            errors.append("Passwords do not match.")
        if not full_name:
            errors.append("Full name is required.")
        if User.query.filter_by(email=email).first():
            errors.append("An account with that email already exists.")
        if User.query.filter_by(username=username).first():
            errors.append("That username is taken.")

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("auth/agent_signup.html",
                                   username=username, email=email,
                                   full_name=full_name,
                                   license_number=license_number,
                                   brokerage=brokerage, phone=phone,
                                   bio=bio, service_areas=service_areas)

        # Create user with agent role
        user = User(username=username, email=email, role="agent")
        user.set_password(password)
        db.session.add(user)
        db.session.flush()  # get user.id

        # Create agent profile (pending approval)
        profile = AgentProfile(
            user_id=user.id,
            full_name=full_name,
            license_number=license_number or None,
            brokerage=brokerage or None,
            phone=phone or None,
            bio=bio or None,
            service_areas=service_areas or None,
            status="pending",
        )
        db.session.add(profile)
        db.session.commit()

        # Send verification email
        try:
            _send_verification_email(user)
            flash("Agent account created! Check your email to verify, then await "
                  "approval from the site owner.", "success")
        except Exception as exc:
            current_app.logger.error(f"Mail send failed: {exc}")
            flash("Account created, but we couldn't send the verification email. "
                  "You can request a new one from the login page.", "warning")

        return _site_redirect("auth.login")

    return render_template("auth/agent_signup.html")


# ── Agent masquerade ─────────────────────────────────────────────

@auth_bp.route("/masquerade/<int:user_id>", methods=["POST"])
@login_required
def masquerade(user_id):
    """Agent/master logs in as another user to view/act on their behalf."""
    from flask import session

    # Master (or someone masquerading from master) can masquerade as anyone
    # Check if the real original user is master (supports chaining: master→agent→principal)
    original_id = session.get("masquerade_original_id")
    real_master = False
    if current_user.is_master:
        real_master = True
    elif original_id:
        original = db.session.get(User, original_id)
        if original and original.is_master:
            real_master = True

    if real_master:
        target = db.session.get(User, user_id)
        if not target:
            flash("User not found.", "danger")
            return _site_redirect("dashboard.index")
        # Always store the TRUE original (master), not intermediate hops
        if not original_id:
            session["masquerade_original_id"] = current_user.id
        login_user(target)
        flash(
            f"Previewing as <strong>{target.username}</strong> ({target.role}). "
            f'<a href="{_site_url("auth.end_masquerade")}" class="alert-link">End Preview</a>',
            "info",
        )
        return _site_redirect("dashboard.index")

    if not current_user.is_agent:
        flash("Access denied.", "danger")
        return _site_redirect("dashboard.index")

    client = db.session.get(User, user_id)
    if not client:
        flash("Client not found.", "danger")
        return _site_redirect("dashboard.agent_dashboard")

    # Verify this client belongs to the requesting agent
    if client.agent_id != current_user.agent_profile.id:
        flash("You can only preview your own clients.", "danger")
        return _site_redirect("dashboard.agent_dashboard")

    # Store original id so we can return — don't overwrite if already chaining
    if "masquerade_original_id" not in session:
        session["masquerade_original_id"] = current_user.id
    login_user(client)
    flash(
        f"Previewing as <strong>{client.username}</strong>. "
        f'<a href="{_site_url("auth.end_masquerade")}" class="alert-link">End Preview →</a>',
        "info",
    )
    return _site_redirect("dashboard.index")


@auth_bp.route("/end-masquerade")
@login_required
def end_masquerade():
    """Return to the agent's own account after masquerading as a client."""
    from flask import session

    original_id = session.pop("masquerade_original_id", None)
    if not original_id:
        return _site_redirect("dashboard.index")

    original = db.session.get(User, original_id)
    if not original:
        logout_user()
        return _site_redirect("auth.login")

    login_user(original)
    if original.is_master:
        flash("Returned to your master account.", "success")
        return _site_redirect("dashboard.index")
    flash("Returned to your agent account.", "success")
    return _site_redirect("dashboard.agent_dashboard")
