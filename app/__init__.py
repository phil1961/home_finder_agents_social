# ─────────────────────────────────────────────
# File: app/__init__.py
# App Version: 2026.03.14 | File Version: 1.7.0
# Last Modified: 2026-03-18
# ─────────────────────────────────────────────
"""Flask application factory."""
import logging
import os
import re
import threading
from flask import Flask, g, request, has_request_context, has_app_context
from flask_login import LoginManager
from flask_mail import Mail
from sqlalchemy import create_engine

from app.models import db, User

MODULE_VERSION = "2026.03.07-multitenant"
log = logging.getLogger(__name__)
log.warning(f"__init__.py loaded — version {MODULE_VERSION}")

login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "Create a free account or sign in to unlock that feature."
login_manager.login_message_category = "info"

mail = Mail()

# ── Per-site engine cache (keyed by absolute db_path) ────────────────────────
_site_engines: dict = {}
_engines_lock = threading.Lock()


def _get_site_engine(db_path: str):
    """Return (and cache) a SQLAlchemy engine for the given DB path.
    Creates the DB file and all tables on first access for a new site.
    """
    from pathlib import Path
    abs_path = str(Path(db_path).resolve())
    with _engines_lock:
        if abs_path not in _site_engines:
            Path(abs_path).parent.mkdir(parents=True, exist_ok=True)
            engine = create_engine(
                f"sqlite:///{abs_path}",
                connect_args={"check_same_thread": False},
            )
            _site_engines[abs_path] = engine
        return _site_engines[abs_path]


def _release_site_engine(db_path: str) -> bool:
    """Dispose and evict a site engine from the cache.

    Call this before renaming or deleting a site DB file on Windows,
    where open file handles prevent filesystem operations.

    Returns True if an engine was found and disposed, False otherwise.
    """
    from pathlib import Path
    abs_path = str(Path(db_path).resolve())
    with _engines_lock:
        engine = _site_engines.pop(abs_path, None)
    if engine is not None:
        try:
            engine.dispose()
            log.info(f"_release_site_engine: disposed engine for {abs_path}")
        except Exception as e:
            log.warning(f"_release_site_engine: dispose error for {abs_path}: {e}")
        return True
    return False


def _wal_checkpoint(db_path: str) -> None:
    """Run WAL checkpoint on a SQLite DB to collapse -wal/-shm into the main file.

    Runs TRUNCATE first (fastest, resets WAL to empty) then FULL as a fallback
    if there are active readers. Safe to call on any SQLite DB at any time.
    Does nothing if the file doesn't exist or isn't a SQLite WAL-mode DB.
    """
    import sqlite3 as _sqlite3
    from pathlib import Path
    abs_path = str(Path(db_path).resolve())
    if not Path(abs_path).exists():
        return
    try:
        conn = _sqlite3.connect(abs_path, timeout=5)
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        conn.execute("PRAGMA wal_checkpoint(FULL)")
        conn.close()
        log.info(f"_wal_checkpoint: checkpointed {abs_path}")
    except Exception as e:
        log.warning(f"_wal_checkpoint: could not checkpoint {abs_path}: {e}")


@login_manager.user_loader
def load_user(user_id):
    """Load user by ID, but only if the session's site matches the current request site.
    Prevents cross-site session bleed when the same user ID exists in multiple site DBs."""
    from flask import session as flask_session
    session_site = flask_session.get("_site_key")
    current_site = getattr(g, "site", {}).get("site_key") if hasattr(g, "site") else None
    if session_site and current_site and session_site != current_site:
        log.info(f"load_user: site mismatch session={session_site!r} vs request={current_site!r} — refusing login")
        return None
    return db.session.get(User, int(user_id))


def create_app(config_class=None):
    app = Flask(__name__, template_folder="templates", static_folder="static")

    # Load config
    if config_class is None:
        from config import Config
        config_class = Config
    app.config.from_object(config_class)

    # Ensure instance folder exists
    os.makedirs(app.instance_path, exist_ok=True)

    # Init extensions
    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)

    # ── Multi-tenant session proxy ─────────────────────────────────
    # FSA bakes the default engine into the sessionmaker at init_app time
    # and calls db.session() as a function (via Model.query). We replace
    # db.session with a callable wrapper that creates per-request sessions
    # from g.site_engine instead of the cached default engine.
    from sqlalchemy.orm import Session as _SASession

    _default_scoped_session = db.session  # keep for teardown/fallback

    class _SiteRoutedSession:
        """Callable session wrapper.

        - When called as a function (Model.query uses session()),
          returns the current per-request Session.
        - Attribute access is proxied to the current Session so that
          db.session.query(...), db.session.add(...) etc. all work.
        """
        def _current(self):
            from flask import g, has_app_context
            if has_app_context() and hasattr(g, "site_engine"):
                if not hasattr(g, "_site_session"):
                    g._site_session = _SASession(g.site_engine)
                    app.logger.debug(
                        f"_SiteRoutedSession: new session → {g.site.get('db_path','?')!r}")
                return g._site_session
            return _default_scoped_session

        # callable — FSA Model.query does cls.__fsa__.session()
        def __call__(self, *a, **kw):
            return self._current()

        # FSA teardown calls db.session.remove() — close and discard the site session
        def remove(self):
            session = g.pop("_site_session", None)
            if session is not None:
                session.close()
            else:
                # fallback to default scoped session remove
                try:
                    _default_scoped_session.remove()
                except Exception:
                    pass

        # attribute proxy — db.session.query / .add / .get / .execute etc.
        def __getattr__(self, name):
            return getattr(self._current(), name)

    db.session = _SiteRoutedSession()

    @app.teardown_appcontext
    def _close_site_session(exc):
        session = g.pop("_site_session", None)
        if session is not None:
            if exc:
                session.rollback()
            session.close()

    # ── Registry init ─────────────────────────────────────────────
    from app.services.registry import init_registry, get_site, get_default_site_key
    init_registry()

    # ── Per-request site DB routing ───────────────────────────────
    @app.before_request
    def select_site():
        """Determine active site from g.site_key (set by SitePathMiddleware)
        or X-HomeFinder-Site header, then bind the correct DB engine.
        """
        default_key = get_default_site_key()
        # SitePathMiddleware sets HTTP_X_HOMEFINDER_SITE from the URL path
        site_key = (
            request.environ.get("HTTP_X_HOMEFINDER_SITE")
            or request.headers.get("X-HomeFinder-Site", default_key)
        ).strip().lower()

        app.logger.debug(f"select_site: key={site_key!r} path={request.path!r}")
        site = get_site(site_key)
        if site is None:
            app.logger.warning(f"select_site: {site_key!r} not found, falling back to default {default_key!r}")
            site = get_site(default_key)
        if site:
            app.logger.debug(f"select_site: bound to db_path={site['db_path']!r}")
            g.site = site
            g.site_engine = _get_site_engine(site["db_path"])
            if getattr(app, "_sites_initialized", None) is None:
                app._sites_initialized = set()
            if site_key not in app._sites_initialized:
                try:
                    db.metadata.create_all(g.site_engine)
                    from app.migrations import apply_all
                    apply_all(g.site_engine, app.logger)
                    app._sites_initialized.add(site_key)
                except Exception as exc:
                    app.logger.warning(f"Schema init for {site_key}: {exc}")

    # ── Inject g.site into all templates ─────────────────────────
    @app.context_processor
    def inject_site():
        from flask import url_for as _url_for
        site = getattr(g, "site", None)
        site_key = site["site_key"] if site else None

        def site_url(endpoint, **kwargs):
            """Like url_for() but prepends /site/<key> when a site is active."""
            base = _url_for(endpoint, **kwargs)
            if site_key:
                # Insert /site/<key> after the app root prefix
                # e.g. /home_finder_agents/preferences → /home_finder_agents/site/charleston/preferences
                from flask import request as _req
                # Find the script root (everything before the first route segment)
                script = _req.script_root or ""
                if base.startswith(script):
                    path = base[len(script):]
                    return f"{script}/site/{site_key}{path}"
            return base

        # Inject all sites list for master nav dropdown
        _all_sites = None
        try:
            from flask_login import current_user as _su
            if _su.is_authenticated and _su.is_master:
                from app.services.registry import get_all_sites as _gas
                _all_sites = _gas()
        except Exception:
            pass

        return {"current_site": site, "site_url": site_url, "all_sites": _all_sites}

    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.site_manager import site_manager_bp
    from app.routes.docs import docs_bp
    from app.routes.social import social_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(site_manager_bp)
    app.register_blueprint(docs_bp)
    app.register_blueprint(social_bp)

    # Serve service worker from app root so its scope covers the whole app
    @app.route("/sw.js")
    def service_worker():
        from flask import send_from_directory
        return send_from_directory(
            app.static_folder, "sw.js",
            mimetype="application/javascript",
        )

    # Import social models so db.create_all() picks up their tables
    from importlib import import_module as _imp
    _imp("app.models_social")

    # Create tables on first run + apply all migrations
    with app.app_context():
        db.create_all()
        from app.migrations import apply_all
        apply_all(db.engine, app.logger)

    # ── Jinja2 filters ────────────────────────────────────────────
    import json as _json

    @app.template_filter("from_json")
    def from_json_filter(value):
        if not value:
            return []
        try:
            return _json.loads(value)
        except (ValueError, TypeError):
            return []

    # ── Version context processor ─────────────────────────────────
    @app.context_processor
    def inject_version():
        return {"app_version": app.config.get("APP_VERSION", "")}

    @app.context_processor
    def inject_siblings():
        """For master users: inject sibling accounts (same email) for role switching."""
        from flask_login import current_user as _cu
        if _cu.is_authenticated and _cu.is_master:
            siblings = User.query.filter_by(email=_cu.email).order_by(User.id).all()
            return {"siblings": siblings}
        return {"siblings": []}

    @app.context_processor
    def inject_help_and_power():
        """Inject help_level, power_mode, and ai_mode for UI customization."""
        from flask_login import current_user as _cu
        from flask import session as _sess
        if _cu.is_authenticated:
            try:
                prefs = _cu.get_prefs()
                return {
                    "help_level": prefs.get("help_level", 2),
                    "power_mode": prefs.get("power_mode", "high"),
                    "ai_mode": prefs.get("ai_mode", "on"),
                }
            except Exception:
                pass
        else:
            guest = _sess.get("guest_prefs", {})
            return {
                "help_level": guest.get("help_level", 2),
                "power_mode": guest.get("power_mode", "low"),
                "ai_mode": guest.get("ai_mode", "off"),
            }
        return {"help_level": 2, "power_mode": "high", "ai_mode": "on"}

    @app.context_processor
    def inject_feedback_count():
        """For owners: inject unread feedback count for nav badge."""
        from flask_login import current_user as _cu
        if _cu.is_authenticated and _cu.is_owner:
            try:
                from app.models_social import Feedback
                count = Feedback.query.filter_by(is_read=False).count()
                return {"feedback_unread_count": count}
            except Exception:
                pass
        return {"feedback_unread_count": 0}

    # ── Request logger ────────────────────────────────────────────
    @app.before_request
    def log_request():
        app.logger.debug(f"{request.method} {request.path}")

    # ── Wrap with WSGI middleware for /site/<key>/ URL routing ───
    app.wsgi_app = SitePathMiddleware(app.wsgi_app)

    # ── Nightly pipeline ──────────────────────────────────────────
    # Handled by Windows Task Scheduler → bin/scheduled_pipeline.py
    # (APScheduler removed — unreliable under IIS idle-timeout recycling)

    # ── Registry write timeout fix ────────────────────────────────
    # (applied in registry.py _connect())

    # ── Debug-mode WAL cleanup ────────────────────────────────────
    # In development, WAL and SHM files accumulate quickly and clutter
    # the instance/ directory. Checkpoint all active site DBs on startup
    # so you begin each dev session with a clean slate.
    if app.debug:
        with app.app_context():
            try:
                from app.services.registry import get_all_sites
                for _site in get_all_sites():
                    if _site.get("active"):
                        _wal_checkpoint(_site["db_path"])
            except Exception as _e:
                log.warning(f"Debug WAL cleanup failed: {_e}")

    return app


class SitePathMiddleware:
    """WSGI middleware that extracts /site/<key>/ from the URL path
    before Flask's router runs, sets HTTP_X_HOMEFINDER_SITE in environ,
    and strips the /site/<key> segment so existing routes match unchanged.

    Examples:
      /home_finder_agents/site/charleston/preferences
        → PATH_INFO: /home_finder_agents/preferences
        → HTTP_X_HOMEFINDER_SITE: charleston

      /home_finder_agents/site/bathwv/
        → PATH_INFO: /home_finder_agents/
        → HTTP_X_HOMEFINDER_SITE: bathwv
    """
    _PATTERN = re.compile(r'/site/([a-z0-9_-]+)(/?)')

    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        path = environ.get("PATH_INFO", "")
        m = self._PATTERN.search(path)
        if m:
            site_key = m.group(1).lower()
            environ["HTTP_X_HOMEFINDER_SITE"] = site_key
            new_path = path[:m.start()] + (m.group(2) if path[m.end():] == "" else path[m.end():])
            environ["PATH_INFO"] = new_path or "/"
            log.debug(f"SitePathMiddleware: extracted site={site_key!r}, path {path!r} → {environ['PATH_INFO']!r}")
        return self.wsgi_app(environ, start_response)


