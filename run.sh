#!/usr/bin/env bash
set -euo pipefail

# run.sh - helper to build/run/test/plot the project using Bazel (with fallbacks)
# Usage: ./run.sh [build|run|test|plot|all|help] [-- additional args passed to binary]

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
  ./run.sh plot         Run the plotting step (bazel run //main:plot or python3 main/plot.py)
  ./run.sh all          Build, run, then plot (in that order)
  ./run.sh help         Show this help

Notes:
  - This script expects Bazel to be installed on your system. If Bazel is missing,
    the script will fail but will provide a helpful message.
  - The project currently contains hard-coded Windows paths in `main/main.cpp`.
    You may need to update `main/main.cpp` to use relative paths or pass file
    locations via command-line arguments before running the binary.
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
  # pass any remaining args to the binary
  $BAZEL run $BAZEL_FLAGS //main:main -- "$@"
}

run_test() {
  if [[ -z "$BAZEL" ]]; then
    echo "ERROR: Bazel not found on PATH. Install Bazel and retry." >&2
    return 2
  fi
  echo "Running unit tests //object_tracking/test:unit_tests..."
  $BAZEL test $BAZEL_FLAGS //object_tracking/test:unit_tests
}

run_plot() {
  if [[ -n "$BAZEL" ]]; then
    if $BAZEL run $BAZEL_FLAGS //main:plot; then
      return 0
    fi
  fi
  if command -v python3 >/dev/null 2>&1 && [[ -f main/plot.py ]]; then
    echo "Running main/plot.py with python3..."
    python3 main/plot.py
    return $?
  fi
  echo "No plot target or plot script found; skipping plot." >&2
  return 1
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
