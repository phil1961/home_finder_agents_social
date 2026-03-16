# ─────────────────────────────────────────────
# File: app/utils.py
# App Version: 2026.03.12 | File Version: 1.1.0
# Last Modified: 2026-03-12
# ─────────────────────────────────────────────
"""Shared utility functions for HomeFinder routes."""
from flask import g, redirect, request, url_for


def site_url(endpoint, **kwargs):
    """Build a relative URL that preserves the current site context.

    Same logic as the Jinja2 site_url() helper but usable in Python code.
    """
    base = url_for(endpoint, **kwargs)
    site = getattr(g, "site", None)
    if site:
        script = request.script_root or ""
        key = site["site_key"]
        path = base[len(script):] if base.startswith(script) else base
        return f"{script}/site/{key}{path}"
    return base


def site_redirect(endpoint, **kwargs):
    """Build a redirect response that preserves the current site context.

    Mirrors the site_url() Jinja helper: if g.site is bound, injects
    /site/<key> into the URL so the user stays in their site after auth
    actions (login, logout, verify, register, etc.).
    """
    base = url_for(endpoint, **kwargs)
    site = getattr(g, "site", None)
    if site:
        script = request.script_root or ""
        key = site["site_key"]
        path = base[len(script):] if base.startswith(script) else base
        return redirect(f"{script}/site/{key}{path}")
    return redirect(base)


def site_url_external(endpoint, **kwargs):
    """Build an absolute URL that preserves the current site context.

    Used for email links — same logic as site_redirect but returns a
    string instead of a redirect response.
    """
    base = url_for(endpoint, _external=True, **kwargs)
    site = getattr(g, "site", None)
    if site:
        script = request.script_root or ""
        key = site["site_key"]
        # base is absolute: https://host/script_root/auth/...
        # Insert /site/<key> after the script_root portion
        from urllib.parse import urlparse, urlunparse
        parsed = urlparse(base)
        path = parsed.path
        if script and path.startswith(script):
            path = path[len(script):]
        new_path = f"{script}/site/{key}{path}"
        base = urlunparse(parsed._replace(path=new_path))
    return base
