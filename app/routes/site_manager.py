# v20260310-1
"""
app/routes/site_manager.py
───────────────────────────
Owner-only routes for managing HomeFinder site instances.

Routes
──────
GET  /admin/sites               — list all sites
POST /admin/sites/create        — create a new site + initialize its DB
POST /admin/sites/<key>/edit    — update site config
POST /admin/sites/<key>/toggle  — activate / deactivate
POST /admin/sites/<key>/delete  — permanently remove site record
GET  /admin/sites/<key>/nginx   — show nginx config snippet for this site
GET  /admin/sites/api/list      — JSON list for dashboard widgets
"""

import json
import os
from pathlib import Path
from datetime import datetime, timezone

from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, jsonify, abort, current_app)
from flask_login import login_required, current_user

from app.services import registry

site_manager_bp = Blueprint("site_manager", __name__)


def _owner_required():
    """Abort 403 unless the current user is the master."""
    if not current_user.is_authenticated or not current_user.is_master:
        abort(403)


def _init_site_db(db_path: str, app=None):
    """Create schema + run migrations in a brand-new site DB."""
    from app.models import db
    from app import _get_site_engine
    from app.migrations import apply_all

    _app = app or current_app._get_current_object()
    engine = _get_site_engine(db_path)

    # Create all ORM tables, then run consolidated migrations
    db.metadata.create_all(engine)
    apply_all(engine, _app.logger)
    _app.logger.info(f"Site DB initialized: {db_path}")


# ── Routes ─────────────────────────────────────────────────────────────────────

@site_manager_bp.route("/admin/sites")
@login_required
def sites_list():
    _owner_required()
    sites = registry.get_all_sites()

    # Enrich each site with live listing count from its own DB
    from app import _get_site_engine
    from sqlalchemy import text as sql_text
    for site in sites:
        try:
            engine = _get_site_engine(site["db_path"])
            with engine.connect() as conn:
                result = conn.execute(
                    sql_text("SELECT COUNT(*) FROM listings WHERE status = 'active'")
                ).fetchone()
                site["live_count"] = result[0] if result else 0
        except Exception:
            site["live_count"] = site.get("listing_count", 0)

    return render_template("admin_sites.html", sites=sites)


@site_manager_bp.route("/admin/sites/create", methods=["POST"])
@login_required
def sites_create():
    _owner_required()

    site_key   = request.form.get("site_key", "").strip().lower().replace(" ", "_")
    disp_name  = request.form.get("display_name", "").strip()
    db_filename = request.form.get("db_filename", "").strip() or f"{site_key}.db"
    lat        = float(request.form.get("map_center_lat") or 39.5)
    lon        = float(request.form.get("map_center_lon") or -98.35)
    zoom       = int(request.form.get("map_zoom") or 10)
    owner_email = request.form.get("owner_email", "").strip()

    # Zip codes — comma-separated text field
    raw_zips = request.form.get("zip_codes", "")
    zip_list = [z.strip() for z in raw_zips.replace("\n", ",").split(",") if z.strip()]
    zip_json = json.dumps(zip_list) if zip_list else None

    # Map bounds — [[sw_lat,sw_lon],[ne_lat,ne_lon]]
    sw_lat = request.form.get("sw_lat"); sw_lon = request.form.get("sw_lon")
    ne_lat = request.form.get("ne_lat"); ne_lon = request.form.get("ne_lon")
    bounds_json = None
    if all([sw_lat, sw_lon, ne_lat, ne_lon]):
        try:
            bounds_json = json.dumps([
                [float(sw_lat), float(sw_lon)],
                [float(ne_lat), float(ne_lon)]
            ])
        except ValueError:
            pass

    if not site_key or not disp_name:
        flash("Site key and display name are required.", "danger")
        return redirect(url_for("site_manager.sites_list"))

    # Build DB path relative to project root
    project_root = Path(current_app.root_path).parent
    db_path = str(Path("instance") / db_filename)
    abs_db_path = str(project_root / db_path)

    try:
        registry.create_site(
            site_key=site_key,
            display_name=disp_name,
            db_path=db_path,
            map_center_lat=lat,
            map_center_lon=lon,
            map_zoom=zoom,
            map_bounds_json=bounds_json,
            zip_codes_json=zip_json,
            owner_email=owner_email,
        )
        # Initialize the new DB schema
        _init_site_db(abs_db_path)

        # ── Seed all operator accounts into new site DB ────────────
        # Copies every account with the master's email from the source
        # (current) site DB — preserving roles, password hashes, and
        # verified status.  Uses INSERT OR REPLACE so re-creating a site
        # refreshes the accounts rather than silently skipping them.
        try:
            master = current_user._get_current_object()
            import sqlite3 as _sqlite3

            # Source DB = the site the master is currently logged into
            from flask import g
            src_db_path = None
            if hasattr(g, "site") and g.site:
                src_db_path = str(project_root / g.site.get("db_path", ""))

            seeded = 0
            if src_db_path and Path(src_db_path).exists():
                src = _sqlite3.connect(src_db_path, timeout=10)
                src.row_factory = _sqlite3.Row

                # 1. Copy user accounts
                accounts = src.execute(
                    "SELECT username, email, password_hash, role, is_verified "
                    "FROM users WHERE email = ?",
                    (master.email,)
                ).fetchall()

                # 2. Find agent profiles for agent-role users
                agent_usernames = [a["username"] for a in accounts if a["role"] == "agent"]
                agent_profiles = []
                if agent_usernames:
                    placeholders = ",".join("?" * len(agent_usernames))
                    agent_profiles = src.execute(
                        f"SELECT ap.*, u.username AS agent_username "
                        f"FROM agent_profiles ap "
                        f"JOIN users u ON u.id = ap.user_id "
                        f"WHERE u.username IN ({placeholders})",
                        agent_usernames
                    ).fetchall()

                # 3. Find which principals are assigned to which agents
                principal_agents = {}  # principal_username → agent_username
                principal_usernames = [a["username"] for a in accounts if a["role"] == "principal"]
                if principal_usernames:
                    placeholders = ",".join("?" * len(principal_usernames))
                    rows = src.execute(
                        f"SELECT u.username AS principal_username, "
                        f"       agent_u.username AS agent_username "
                        f"FROM users u "
                        f"JOIN agent_profiles ap ON u.agent_id = ap.id "
                        f"JOIN users agent_u ON agent_u.id = ap.user_id "
                        f"WHERE u.username IN ({placeholders})",
                        principal_usernames
                    ).fetchall()
                    for row in rows:
                        principal_agents[row["principal_username"]] = row["agent_username"]

                src.close()

                # Write to destination DB
                dest = _sqlite3.connect(abs_db_path, timeout=10)
                dest.execute("PRAGMA journal_mode=WAL")

                # Insert users (without agent_id for now)
                for acct in accounts:
                    dest.execute("""
                        INSERT OR REPLACE INTO users
                            (username, email, password_hash, role,
                             is_verified, created_at)
                        VALUES (?, ?, ?, ?, 1, datetime('now'))
                    """, (acct["username"], acct["email"],
                          acct["password_hash"], acct["role"]))
                    seeded += 1

                # Insert agent profiles
                for ap in agent_profiles:
                    # Get the agent's user_id in the new DB
                    row = dest.execute(
                        "SELECT id FROM users WHERE username = ?",
                        (ap["agent_username"],)
                    ).fetchone()
                    if row:
                        agent_user_id = row[0]
                        dest.execute("""
                            INSERT OR REPLACE INTO agent_profiles
                                (user_id, full_name, license_number, brokerage,
                                 phone, bio, service_areas, status, approved_at,
                                 created_at, brand_color, brand_logo_url,
                                 brand_icon, brand_tagline, brand_tagline_style)
                            VALUES (?, ?, ?, ?, ?, ?, ?, 'approved',
                                    datetime('now'), datetime('now'),
                                    ?, ?, ?, ?, ?)
                        """, (agent_user_id, ap["full_name"],
                              ap["license_number"], ap["brokerage"],
                              ap["phone"], ap["bio"], ap["service_areas"],
                              ap["brand_color"], ap["brand_logo_url"],
                              ap["brand_icon"], ap["brand_tagline"],
                              ap["brand_tagline_style"]))
                        current_app.logger.info(
                            f"Seeded agent profile '{ap['full_name']}' "
                            f"for user {ap['agent_username']}")

                # Link principals to their agents
                for principal_uname, agent_uname in principal_agents.items():
                    # Find agent profile id in new DB
                    row = dest.execute(
                        "SELECT ap.id FROM agent_profiles ap "
                        "JOIN users u ON u.id = ap.user_id "
                        "WHERE u.username = ?",
                        (agent_uname,)
                    ).fetchone()
                    if row:
                        dest.execute(
                            "UPDATE users SET agent_id = ? WHERE username = ?",
                            (row[0], principal_uname)
                        )
                        current_app.logger.info(
                            f"Linked principal '{principal_uname}' to "
                            f"agent '{agent_uname}' (profile #{row[0]})")

                dest.commit()
                dest.close()
                current_app.logger.info(
                    f"Seeded {seeded} operator account(s) into {db_path}")
            else:
                # Fallback: no source DB available — seed just this user as owner
                dest = _sqlite3.connect(abs_db_path, timeout=10)
                dest.execute("PRAGMA journal_mode=WAL")
                dest.execute("""
                    INSERT OR REPLACE INTO users
                        (username, email, password_hash, role,
                         is_verified, created_at)
                    VALUES (?, ?, ?, 'owner', 1, datetime('now'))
                """, (master.username, master.email, master.password_hash))
                dest.commit()
                dest.close()
                current_app.logger.warning(
                    f"No source DB found — seeded only owner account into {db_path}")
        except Exception as seed_exc:
            current_app.logger.warning(
                f"Could not seed operator accounts into {db_path}: {seed_exc}")

        flash(f"Site '{disp_name}' created and database initialized.", "success")
    except ValueError as e:
        flash(str(e), "danger")
    except Exception as e:
        current_app.logger.error(f"Site create error: {e}")
        flash(f"Error creating site: {e}", "danger")

    return redirect(url_for("site_manager.sites_list"))


@site_manager_bp.route("/admin/sites/<site_key>/edit", methods=["POST"])
@login_required
def sites_edit(site_key):
    _owner_required()

    fields = {}
    for f in ["display_name", "db_path", "owner_email"]:
        val = request.form.get(f, "").strip()
        if val:
            fields[f] = val
    for f in ["map_center_lat", "map_center_lon"]:
        val = request.form.get(f)
        if val:
            try: fields[f] = float(val)
            except ValueError: pass
    for f in ["map_zoom", "max_fetches_per_run"]:
        val = request.form.get(f)
        if val is not None and val.strip() != '':
            try: fields[f] = int(val)
            except ValueError: pass

    # Scheduler locked: checkbox sends "1" when checked, absent when unchecked
    if "scheduler_locked" in request.form:
        fields["scheduler_locked"] = 1
    elif any(k in request.form for k in ["scheduler_locked", "max_fetches_per_run"]):
        # Only clear if this form included the lock field (not the edit-config form)
        fields["scheduler_locked"] = 0

    raw_zips = request.form.get("zip_codes", "")
    if raw_zips.strip():
        zip_list = [z.strip() for z in raw_zips.replace("\n", ",").split(",") if z.strip()]
        fields["zip_codes_json"] = json.dumps(zip_list)

    sw_lat = request.form.get("sw_lat"); sw_lon = request.form.get("sw_lon")
    ne_lat = request.form.get("ne_lat"); ne_lon = request.form.get("ne_lon")
    if all([sw_lat, sw_lon, ne_lat, ne_lon]):
        try:
            fields["map_bounds_json"] = json.dumps([
                [float(sw_lat), float(sw_lon)],
                [float(ne_lat), float(ne_lon)]
            ])
        except ValueError:
            pass

    registry.update_site(site_key, **fields)
    flash("Site updated.", "success")
    return redirect(url_for("site_manager.sites_list"))


@site_manager_bp.route("/admin/sites/<site_key>/toggle", methods=["POST"])
@login_required
def sites_toggle(site_key):
    _owner_required()
    site = registry.get_site_any(site_key)
    if not site:
        abort(404)
    new_state = 0 if site["active"] else 1
    registry.update_site(site_key, active=new_state)
    status = "activated" if new_state else "deactivated"
    flash(f"Site '{site['display_name']}' {status}.", "success")
    return redirect(url_for("site_manager.sites_list"))


@site_manager_bp.route("/admin/sites/<site_key>/delete", methods=["POST"])
@login_required
def sites_delete(site_key):
    _owner_required()
    site = registry.get_site_any(site_key)
    if not site:
        abort(404)

    # Checkpoint the WAL first so -wal/-shm files are collapsed into the
    # main DB, then release the engine (closes pooled connections) before
    # attempting the rename — both steps are needed on Windows.
    from app import _wal_checkpoint, _release_site_engine
    project_root = Path(current_app.root_path).parent
    db_path = site.get("db_path", "")
    abs_db = project_root / db_path
    _wal_checkpoint(str(abs_db))
    _release_site_engine(str(abs_db))

    renamed_to = None
    rename_error = None
    if abs_db.exists():
        dest = abs_db.with_suffix(".db.deleted")
        if dest.exists():
            from datetime import datetime as _dt
            stamp = _dt.now().strftime("%Y%m%d_%H%M%S")
            dest = abs_db.with_name(abs_db.stem + f"_{stamp}.db.deleted")
        try:
            abs_db.rename(dest)
            renamed_to = dest.name
            current_app.logger.info(f"Renamed {abs_db} to {dest}")
        except OSError as e:
            rename_error = str(e)
            current_app.logger.warning(f"Could not rename DB for {site_key}: {e}")

    registry.delete_site(site_key)

    if renamed_to:
        flash(
            f"Site '{site['display_name']}' removed. "
            f"Database renamed to <code>{renamed_to}</code> — "
            f"restore by renaming it back to <code>{abs_db.name}</code> and re-adding the site.",
            "warning",
        )
    elif rename_error:
        flash(
            f"Site '{site['display_name']}' removed from registry, but the database file "
            f"could not be renamed — it may still be open in HeidiSQL or another tool. "
            f"Close any connections to <code>{abs_db.name}</code> and rename it manually. "
            f"Error: {rename_error}",
            "danger",
        )
    else:
        flash(
            f"Site '{site['display_name']}' removed from registry. "
            f"DB file at '{db_path}' was not found — nothing to rename.",
            "warning",
        )
    return redirect(url_for("site_manager.sites_list"))


@site_manager_bp.route("/admin/sites/<site_key>/nginx")
@login_required
def sites_nginx(site_key):
    _owner_required()
    site = registry.get_site_any(site_key)
    if not site:
        abort(404)
    return jsonify({"nginx": _build_nginx_snippet(site)})


@site_manager_bp.route("/admin/sites/api/list")
@login_required
def sites_api_list():
    _owner_required()
    sites = registry.get_all_sites()
    return jsonify(sites)


# ── Nginx snippet generator ────────────────────────────────────────────────────

def _build_nginx_snippet(site: dict) -> str:
    key = site["site_key"]
    return f"""# HomeFinder — {site['display_name']}
# Add this inside your nginx server block.

location /home_finder_agents_social/ {{
    proxy_pass         http://127.0.0.1:5000;
    proxy_set_header   Host              $host;
    proxy_set_header   X-Real-IP         $remote_addr;
    proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
    proxy_set_header   X-HomeFinder-Site {key};
}}"""
