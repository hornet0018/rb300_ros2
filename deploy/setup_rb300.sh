#!/usr/bin/env bash
set -euo pipefail
# First-time setup of the RB300 A/B deployment layout on the robot.
# Copies the launcher and installs the systemd service.
#
# Usage:
#   sudo ./setup_rb300.sh

APP_ROOT="${RB300_TARGET:-/opt/app/rb300}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

mkdir -p "$APP_ROOT"
install -m 0755 "$SCRIPT_DIR/start.sh" "$APP_ROOT/start.sh"
install -m 0644 "$SCRIPT_DIR/rb300.service" /etc/systemd/system/rb300.service
systemctl daemon-reload
systemctl enable rb300.service

echo "[rb300-setup] installed $APP_ROOT/start.sh and rb300.service"
echo "[rb300-setup] next: ./update_rb300.sh (downloads the first release)"
