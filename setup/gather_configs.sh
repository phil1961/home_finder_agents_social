#!/bin/bash
# ─────────────────────────────────────────────
# gather_configs.sh
# Copies important deployment config files into
# /home/homefinder/home_finder_agents_social/setup/
# Prepends a comment to each file showing its production location.
# Run as root from anywhere.
# ─────────────────────────────────────────────

SETUP_DIR="/home/homefinder/home_finder_agents_social/setup"
mkdir -p "$SETUP_DIR"

copy_with_header() {
    local src="$1"
    local dest_name="$2"
    local comment_char="$3"
    local dest="$SETUP_DIR/$dest_name"

    if [ ! -f "$src" ]; then
        echo "  SKIP  $src (not found)"
        return
    fi

    {
        echo "${comment_char} DEPLOYMENT LOCATION: ${src}"
        echo "${comment_char} Gathered by gather_configs.sh on $(date '+%Y-%m-%d %H:%M:%S')"
        echo ""
        cat "$src"
    } > "$dest"

    echo "  OK    $src -> setup/$dest_name"
}

echo "Gathering config files into $SETUP_DIR ..."
echo ""

copy_with_header \
    "/etc/nginx/conf.d/homefinder.conf" \
    "homefinder.nginx.conf" \
    "#"

copy_with_header \
    "/etc/systemd/system/homefinder.service" \
    "homefinder.service" \
    "#"

copy_with_header \
    "/home/homefinder/home_finder_agents_social/wsgi.py" \
    "wsgi.py" \
    "#"

copy_with_header \
    "/home/homefinder/home_finder_agents_social/run_waitress.py" \
    "run_waitress.py" \
    "#"

# Fix ownership so homefinder user owns the setup dir
chown -R homefinder:homefinder "$SETUP_DIR"

echo ""
echo "Done. Files in $SETUP_DIR:"
ls -lh "$SETUP_DIR"