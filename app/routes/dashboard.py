# ─────────────────────────────────────────────
# File: app/routes/dashboard.py
# App Version: 2026.03.12 | File Version: 1.1.0
# Last Modified: 2026-03-12
# ─────────────────────────────────────────────
"""
app/routes/dashboard.py — Dashboard blueprint assembly.
Imports sub-modules that register routes on dashboard_bp.
"""
from app.routes.dashboard_helpers import dashboard_bp  # noqa: F401

# Import sub-modules to register their routes on dashboard_bp
from app.routes import listings        # noqa: F401
from app.routes import preferences_routes  # noqa: F401
from app.routes import admin_routes    # noqa: F401
from app.routes import ai_routes       # noqa: F401
from app.routes import agent_routes    # noqa: F401
from app.routes import tour_routes     # noqa: F401
from app.routes import watch_routes    # noqa: F401
