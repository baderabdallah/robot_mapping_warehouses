#!/usr/bin/env bash
set -euo pipefail

# run.sh - helper to build/run/test/plot the project using Bazel (with fallbacks)
# Usage: ./run.sh [build|run|test|plot|export|all|help] [-- additional args passed to binary]

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

# Ensure bazelisk uses a Bazel 7.x runtime when present in running containers
export BAZELISK_BAZEL_VERSION=${BAZELISK_BAZEL_VERSION:-7.5.0}
# Prefer WORKSPACE mode on Bazel 8+: disable bzlmod and explicitly enable workspace
BAZEL_FLAGS=${BAZEL_FLAGS:---noenable_bzlmod --enable_workspace}

BAZEL=""
# Prefer bazelisk when available so we can pin Bazel runtime via BAZELISK_BAZEL_VERSION
if command -v bazelisk >/dev/null 2>&1; then
  BAZEL="bazelisk"
elif command -v bazel >/dev/null 2>&1; then
  BAZEL="bazel"
fi

usage() {
  cat <<'EOF'
run.sh - build and run the project

Usage:
  ./run.sh build        Build the main binary (bazel build //main:main)
  ./run.sh run [-- ARGS]  Run the main binary (bazel run //main:main) and pass ARGS to it
  ./run.sh test         Run unit tests (bazel test //object_tracking/test:unit_tests)
  ./run.sh plot         Run the plotting step (bazel run //main:plot or python3 plot/plot.py)
  ./run.sh export [gif|mp4] [OUT] [--fps N]
                        Export the animation to a GIF or MP4 (default OUT is plot/animation.gif)
  ./run.sh all          Build, run, then plot (in that order)
  ./run.sh help         Show this help

Notes:
  - This script expects Bazel to be installed on your system. If Bazel is missing,
    the script will fail but will provide a helpful message.
  - The main binary accepts an optional input path (defaults to main/data.json).
    Outputs are written alongside the input file.
  - Export requires Python packages imageio and imageio-ffmpeg (for mp4). The script
    will attempt to install them automatically if missing.
EOF
}

if [[ ${1-} == "" ]]; then
  usage
  exit 0
fi

cmd="$1"
shift || true

run_build() {
  if [[ -z "$BAZEL" ]]; then
    echo "ERROR: Bazel not found on PATH. Install Bazel (https://bazel.build/) and retry." >&2
    return 2
  fi
  echo "Building //main:main with $BAZEL ($BAZEL_FLAGS)..."
  $BAZEL build $BAZEL_FLAGS //main:main
}

run_run() {
  if [[ -z "$BAZEL" ]]; then
    echo "ERROR: Bazel not found on PATH. Install Bazel and retry." >&2
    return 2
  fi
  echo "Running //main:main (passing through any extra args)..."
  # pass any remaining args to the binary; if none, pass default absolute input path
  if [[ $# -eq 0 ]]; then
    set -- "$ROOT_DIR/main/data.json"
  fi
  $BAZEL run $BAZEL_FLAGS //main:main -- "$@"
}

run_test() {
  if [[ -z "$BAZEL" ]]; then
    echo "ERROR: Bazel not found on PATH. Install Bazel and retry." >&2
    return 2
  fi
  if $BAZEL query $BAZEL_FLAGS //object_tracking/test:unit_tests >/dev/null 2>&1; then
    echo "Running unit tests //object_tracking/test:unit_tests..."
    $BAZEL test $BAZEL_FLAGS //object_tracking/test:unit_tests
  else
    echo "No test target found (//object_tracking/test:unit_tests). Skipping tests."
  fi
}

run_plot() {
  if [[ -n "$BAZEL" ]]; then
    # Only try bazel if the target exists to avoid noisy errors
    if $BAZEL query $BAZEL_FLAGS //main:plot >/dev/null 2>&1; then
      if $BAZEL run $BAZEL_FLAGS //main:plot; then
        return 0
      fi
    fi
  fi
  if command -v python3 >/dev/null 2>&1 && [[ -f plot/plot.py ]]; then
    # Ensure plotting deps are available
  if ! python3 - <<'PY'
import sys
missing = []
for m in ("matplotlib","numpy","tornado"):
    try:
        __import__(m)
    except Exception:
        missing.append(m)
if missing:
    sys.exit(1)
PY
    then
    echo "Installing required Python packages (matplotlib, numpy, tornado) for plotting..."
      if command -v pip3 >/dev/null 2>&1; then
    pip3 install --no-cache-dir matplotlib numpy tornado || true
      fi
    fi
    echo "Running plot/plot.py with python3..."
    if [[ -z "${DISPLAY:-}" ]]; then
      echo "Warning: DISPLAY is not set. If you're on macOS and want an interactive window, run scripts/macos_xquartz_display.sh on the host and set DISPLAY inside the container (e.g., export DISPLAY=host.docker.internal:0)." >&2
    fi
    python3 plot/plot.py
    return $?
  fi
  echo "No plot target or plot script found; skipping plot." >&2
  return 1
}

run_export() {
  local fmt="${1-}"
  local out="${2-}"
  shift || true
  if [[ "$fmt" != "gif" && "$fmt" != "mp4" ]]; then
    # infer from out path if provided
    if [[ -n "$fmt" && "$fmt" == *.gif ]]; then
      out="$fmt"; fmt="gif"; shift || true
    elif [[ -n "$fmt" && "$fmt" == *.mp4 ]]; then
      out="$fmt"; fmt="mp4"; shift || true
    else
      fmt="gif"
    fi
  else
    # consume fmt and potentially out
    if [[ -n "$out" && "$out" != --* ]]; then
      shift || true
    else
      out=""
    fi
  fi

  if [[ -z "$out" ]]; then
    out="plot/animation.$fmt"
  fi

  if ! command -v python3 >/dev/null 2>&1; then
    echo "ERROR: python3 not found; export requires Python." >&2
    return 2
  fi

  # Ensure deps
  if ! python3 - <<'PY'
import sys
missing = []
for m in ("matplotlib","numpy","imageio"):
    try:
        __import__(m)
    except Exception:
        missing.append(m)
if missing:
    sys.exit(1)
PY
  then
    echo "Installing required Python packages (matplotlib, numpy, imageio)..."
    if command -v pip3 >/dev/null 2>&1; then
      pip3 install --no-cache-dir matplotlib numpy imageio || true
    fi
  fi
  if [[ "$fmt" == "mp4" ]]; then
    if ! python3 - <<'PY'
ok=True
try:
    import imageio_ffmpeg  # noqa: F401
except Exception:
    ok=False
import sys
sys.exit(0 if ok else 1)
PY
    then
      echo "Installing imageio-ffmpeg for MP4 export..."
      if command -v pip3 >/dev/null 2>&1; then
        pip3 install --no-cache-dir imageio-ffmpeg || true
      fi
    fi
  fi

  echo "Exporting animation to $out (format: $fmt) ..."
  python3 plot/export.py --format "$fmt" --out "$out" "$@"
}

case "$cmd" in
  build)
    run_build
    ;;
  run)
    run_run "$@"
    ;;
  test)
    run_test
    ;;
  plot)
    run_plot
    ;;
  export)
    run_export "$@"
    ;;
  all)
    run_build
    run_run "$@" || true
    run_plot || true
    ;;
  help|-h|--help)
    usage
    ;;
  *)
    echo "Unknown command: $cmd" >&2
    usage
    exit 2
    ;;
esac

exit 0
