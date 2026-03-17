#!/bin/bash
# cleanup.sh — HomeFinder Social maintenance script
# Run as: ./cleanup.sh

APP_DIR="/home/homefinder/home_finder_agents_social"
LOG_DIR="/var/log/nginx"

echo "======================================"
echo " HomeFinder Social Cleanup"
echo "======================================"

# 1. Remove __pycache__ directories
echo ""
echo "[1/5] Removing __pycache__ directories..."
find "$APP_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
echo "      Done."

# 2. Remove .pyc files
echo "[2/5] Removing .pyc files..."
find "$APP_DIR" -name "*.pyc" -delete 2>/dev/null
echo "      Done."

# 3. Remove Python build artifacts
echo "[3/5] Removing build/dist/egg-info artifacts..."
find "$APP_DIR" -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null
find "$APP_DIR" -type d -name "dist" -exec rm -rf {} + 2>/dev/null
find "$APP_DIR" -type d -name "build" -exec rm -rf {} + 2>/dev/null
echo "      Done."

# 4. Truncate Nginx logs (requires sudo)
echo "[4/5] Truncating Nginx logs..."
sudo truncate -s 0 "$LOG_DIR/access.log" 2>/dev/null && echo "      access.log cleared." || echo "      Skipped (no sudo)."
sudo truncate -s 0 "$LOG_DIR/error.log"  2>/dev/null && echo "      error.log cleared."  || echo "      Skipped (no sudo)."

# 5. Clean /tmp of any leftover Python build files
echo "[5/5] Cleaning /tmp Python build artifacts..."
sudo rm -rf /tmp/Python-*.tgz /tmp/Python-*/ 2>/dev/null
echo "      Done."

echo ""
echo "======================================"
echo " Cleanup complete."
echo "======================================"

# Show disk usage summary
echo ""
df -h /
