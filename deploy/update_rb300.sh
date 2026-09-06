#!/usr/bin/env bash
set -euo pipefail
# RB300 OTA updater: download -> verify -> extract -> A/B swap -> restart.
#
# Usage:
#   sudo ./update_rb300.sh            # install latest release
#   sudo ./update_rb300.sh v1.2.3     # install a specific release tag
#   sudo ./update_rb300.sh --rollback # switch back to the previous version
#
# Env overrides:
#   RB300_REPO     GitHub repo (default: hornet0018/rb300_ros2)
#   RB300_TARGET   install root     (default: /opt/app/rb300)
#   RB300_KEEP     versions to keep (default: 3)
#   RB300_DOWNLOAD base URL override, e.g. internal mirror or S3
#   RB300_GPG_KEY  GPG fingerprint to verify manifest signature (optional)

REPO="${RB300_REPO:-hornet0018/rb300_ros2}"
TARGET="${RB300_TARGET:-/opt/app/rb300}"
KEEP="${RB300_KEEP:-3}"
ARTIFACT="rb300_arm64.tar.gz"
MANIFEST="rb300_manifest.json"
GPG_FP="${RB300_GPG_KEY:-}"

info() { echo "[rb300-update] $*"; }
fail() { echo "[rb300-update] ERROR: $*" >&2; exit 1; }

cmd="${1:-latest}"

if [ "$cmd" = "--rollback" ]; then
  CURRENT="$(readlink "$TARGET/current" 2>/dev/null || true)"
  [ -n "$CURRENT" ] || fail "current symlink not found at $TARGET/current"
  PREV="$(ls -1dt "$TARGET"/ver-* 2>/dev/null | grep -v "^$TARGET/$CURRENT\$" | head -n1 || true)"
  [ -n "$PREV" ] || fail "no previous version found"
  ln -sfn "$(basename "$PREV")" "$TARGET/current.tmp"
  mv -T "$TARGET/current.tmp" "$TARGET/current"
  info "rolled back: current -> $(basename "$PREV")"
  systemctl restart rb300.service 2>/dev/null || info "rb300.service not running"
  exit 0
fi

DL="$TARGET/downloads"
mkdir -p "$DL"

if [ -n "${RB300_DOWNLOAD:-}" ]; then
  BASE="${RB300_DOWNLOAD%/}"
elif [ "$cmd" = "latest" ]; then
  BASE="https://github.com/$REPO/releases/latest/download"
else
  BASE="https://github.com/$REPO/releases/download/$cmd"
fi

info "downloading from $BASE"
curl -fsSL -o "$DL/$MANIFEST" "$BASE/$MANIFEST"
curl -fsSL -o "$DL/$ARTIFACT" "$BASE/$ARTIFACT"

if [ -n "$GPG_FP" ] && curl -fsSL -o "$DL/$MANIFEST.asc" "$BASE/$MANIFEST.asc" 2>/dev/null; then
  gpg --verify "$DL/$MANIFEST.asc" "$DL/$MANIFEST"
  info "manifest signature verified"
fi

EXPECTED_HASH="$(python3 -c "import json; print(json.load(open('$DL/$MANIFEST'))['files'][0]['sha256'])")"
ACTUAL_HASH="$(sha256sum "$DL/$ARTIFACT" | awk '{print $1}')"
[ "$EXPECTED_HASH" = "$ACTUAL_HASH" ] || fail "sha256 mismatch: expected $EXPECTED_HASH got $ACTUAL_HASH"
VERSION="$(python3 -c "import json; print(json.load(open('$DL/$MANIFEST'))['version'])")"
NEWDIR="ver-${ACTUAL_HASH:0:12}"

info "version=$VERSION sha256=$ACTUAL_HASH"
rm -rf "$TARGET/$NEWDIR"
mkdir -p "$TARGET/$NEWDIR/install"
tar -xzf "$DL/$ARTIFACT" -C "$TARGET/$NEWDIR/install"

ln -sfn "$NEWDIR" "$TARGET/current.tmp"
mv -T "$TARGET/current.tmp" "$TARGET/current"
info "switched current -> $NEWDIR"

ls -1dt "$TARGET"/ver-* 2>/dev/null | tail -n +$((KEEP + 1)) | while read -r d; do
  rm -rf "$d"
  info "removed old version $d"
done

if [ -f /etc/systemd/system/rb300.service ]; then
  systemctl restart rb300.service
  info "rb300.service restarted"
else
  info "rb300.service not installed yet - run setup_rb300.sh first"
fi

info "done: $VERSION"
