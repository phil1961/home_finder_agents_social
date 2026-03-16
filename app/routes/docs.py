# ─────────────────────────────────────────────
# File: app/routes/docs.py
# App Version: 2026.03.15 | File Version: 2.0.0
# Last Modified: 2026-03-15
# ─────────────────────────────────────────────
"""
Docs module — role-based access to ./docs folder hierarchy.

Directory structure:
    docs/           — visible to agents, owners, and masters
    docs/agent/     — visible to agents, owners, and masters
    docs/owner/     — visible to owners and masters
    docs/master/    — visible to masters only

Access: agents see docs/ + docs/agent/
        owners see docs/ + docs/agent/ + docs/owner/
        masters see everything
"""
import os
import logging
from flask import (
    Blueprint, render_template, request, jsonify,
    current_app, abort, flash, redirect, url_for
)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

log = logging.getLogger(__name__)

docs_bp = Blueprint("docs", __name__)

ALLOWED_EXTENSIONS = {".md", ".txt", ".html", ".htm"}


def _docs_dir() -> str:
    """Absolute path to the ./docs folder at the project root."""
    return os.path.realpath(os.path.join(current_app.root_path, "..", "docs"))


def _allowed_subdirs() -> list[str]:
    """Return list of subdirectory names the current user may access."""
    dirs = [""]  # root docs/ is always included
    if current_user.is_agent or current_user.is_owner:
        dirs.append("agent")
    if current_user.is_owner:
        dirs.append("owner")
    if current_user.is_master:
        dirs.append("master")
    return dirs


def _safe_path(filename: str) -> str | None:
    """Return absolute path if filename is within an allowed docs subdirectory."""
    # filename may be "AGENT_GUIDE.md" or "agent/AGENT_GUIDE.md"
    parts = filename.replace("\\", "/").split("/")

    # Determine subdirectory and base name
    if len(parts) == 2:
        subdir, base = parts[0], parts[1]
    elif len(parts) == 1:
        subdir, base = "", parts[0]
    else:
        return None  # too many levels

    # Check role access
    if subdir not in _allowed_subdirs():
        return None

    base = secure_filename(base)
    if not base:
        return None
    ext = os.path.splitext(base)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return None

    if subdir:
        full = os.path.realpath(os.path.join(_docs_dir(), subdir, base))
    else:
        full = os.path.realpath(os.path.join(_docs_dir(), base))

    # Guard against path traversal
    if not full.startswith(_docs_dir()):
        return None
    return full


def _ensure_docs_dir():
    base = _docs_dir()
    os.makedirs(base, exist_ok=True)
    for sub in ["agent", "owner", "master"]:
        os.makedirs(os.path.join(base, sub), exist_ok=True)


def _scan_files() -> list[dict]:
    """Scan all allowed directories and return file info dicts."""
    base = _docs_dir()
    files = []
    for subdir in _allowed_subdirs():
        dir_path = os.path.join(base, subdir) if subdir else base
        if not os.path.isdir(dir_path):
            continue
        for name in sorted(os.listdir(dir_path)):
            full = os.path.join(dir_path, name)
            if not os.path.isfile(full):
                continue
            ext = os.path.splitext(name)[1].lower()
            if ext not in ALLOWED_EXTENSIONS:
                continue
            rel_path = f"{subdir}/{name}" if subdir else name
            section_labels = {"": "General", "agent": "Agent", "owner": "Owner", "master": "Master"}
            files.append({
                "name": name,
                "path": rel_path,
                "section": section_labels.get(subdir, subdir),
                "ext": ext,
                "size": os.path.getsize(full),
                "mtime": os.path.getmtime(full),
            })
    return files


# ── Routes ────────────────────────────────────────────────────────────────────

@docs_bp.route("/docs")
@login_required
def index():
    if not (current_user.is_agent or current_user.is_owner):
        abort(403)
    _ensure_docs_dir()
    files = _scan_files()
    return render_template("docs.html", files=files)


@docs_bp.route("/docs/content/<path:filename>")
@login_required
def content(filename):
    """Return raw file content as JSON — called by the viewer via fetch()."""
    if not (current_user.is_agent or current_user.is_owner):
        abort(403)
    path = _safe_path(filename)
    if not path or not os.path.isfile(path):
        abort(404)
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()
    ext = os.path.splitext(filename)[1].lower()
    return jsonify({"filename": filename, "ext": ext, "content": text})


@docs_bp.route("/docs/upload", methods=["POST"])
@login_required
def upload():
    if not current_user.is_owner:
        abort(403)
    _ensure_docs_dir()

    file = request.files.get("file")
    if not file or not file.filename:
        flash("No file selected.", "warning")
        return redirect(url_for("docs.index"))

    # Determine target subdirectory from form
    target_dir = request.form.get("upload_dir", "").strip()
    if target_dir not in _allowed_subdirs():
        target_dir = ""

    name = secure_filename(file.filename)
    ext = os.path.splitext(name)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        flash(f"Unsupported file type '{ext}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}", "danger")
        return redirect(url_for("docs.index"))

    dest_dir = os.path.join(_docs_dir(), target_dir) if target_dir else _docs_dir()
    os.makedirs(dest_dir, exist_ok=True)
    file.save(os.path.join(dest_dir, name))
    label = f"{target_dir}/{name}" if target_dir else name
    log.info(f"docs: uploaded '{label}' by {current_user.username}")
    flash(f"'{label}' uploaded successfully.", "success")
    return redirect(url_for("docs.index"))


@docs_bp.route("/docs/delete/<path:filename>", methods=["POST"])
@login_required
def delete(filename):
    if not current_user.is_owner:
        abort(403)
    path = _safe_path(filename)
    if not path or not os.path.isfile(path):
        flash("File not found.", "warning")
        return redirect(url_for("docs.index"))
    os.remove(path)
    log.info(f"docs: deleted '{filename}' by {current_user.username}")
    flash(f"'{filename}' deleted.", "success")
    return redirect(url_for("docs.index"))
