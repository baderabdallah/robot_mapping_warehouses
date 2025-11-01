#!/usr/bin/env bash
set -euo pipefail

# Configure XQuartz and DISPLAY for Docker/Dev Containers to show GUI apps on macOS.
# Usage: run this on the macOS host BEFORE opening the VS Code dev container
# (or run anytime to ensure XQuartz is ready). It will:
#  - Start XQuartz if needed
#  - Enable TCP connections and IGLX
#  - Add xhost permissions for localhost and your LAN IP
#  - Export a recommended DISPLAY value you can copy into your shell profile if desired
#
# Note: VS Code dev containers don't automatically pass host DISPLAY. If needed,
# you can set DISPLAY inside the container to host.docker.internal:0.

# Start and configure XQuartz automatically (macOS only)
if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "This helper is intended to run on macOS (Darwin). Skipping." >&2
  exit 0
fi

# Ensure XQuartz allows network clients and IGLX
defaults write org.xquartz.X11 nolisten_tcp -bool false || true
defaults write org.xquartz.X11 enable_iglx -bool true || true

# Start XQuartz if not running
if ! pgrep -x "XQuartz" >/dev/null 2>&1; then
  open -g -a XQuartz || true
fi

# Wait until X server is listening on port 6000
for _ in {1..40}; do
  if command -v nc >/dev/null 2>&1; then
    if nc -z 127.0.0.1 6000 >/dev/null 2>&1; then break; fi
  else
    # Fallback: check socket existence
    if ls /private/tmp/com.apple.launchd.*/*:0 >/dev/null 2>&1; then break; fi
  fi
  sleep 0.25
done

# Non-interactive xhost permissions for the chosen DISPLAY targets
# Always allow localhost
if [ -x /opt/X11/bin/xhost ]; then
  DISPLAY=:0 /opt/X11/bin/xhost + 127.0.0.1 >/dev/null 2>&1 || true
fi

# Prefer a reachable TCP DISPLAY for containers: <mac_ip>:0
MAC_IP="$(ipconfig getifaddr en0 2>/dev/null || true)"
if [[ -z "${MAC_IP}" ]]; then
  MAC_IP="$(ipconfig getifaddr en1 2>/dev/null || true)"
fi

RECOMMENDED_DISPLAY="host.docker.internal:0"
if [[ -n "${MAC_IP}" ]]; then
  RECOMMENDED_DISPLAY="${MAC_IP}:0"
  if [ -x /opt/X11/bin/xhost ]; then
    DISPLAY=:0 /opt/X11/bin/xhost + "${MAC_IP}" >/dev/null 2>&1 || true
  fi
fi

cat <<EOF

XQuartz is configured for network clients.
Recommended DISPLAY for containers: ${RECOMMENDED_DISPLAY}

Tips for VS Code dev containers:
- Add this to your container shell once connected (or into ~/.bashrc inside container):
    export DISPLAY=${RECOMMENDED_DISPLAY}
- Or add to devcontainer.json (advanced):
    "containerEnv": { "DISPLAY": "${RECOMMENDED_DISPLAY}" }

If you change XQuartz settings, you may need to quit and re-open XQuartz.
EOF
