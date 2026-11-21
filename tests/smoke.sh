#!/bin/bash
# Runs inside the toolchain image:
#   podman run --rm -v ./tests:/tests:ro,Z tinyos-toolchain:<tag> bash /tests/smoke.sh
# Builds two stock TinyOS apps for TOSSIM and runs a short simulation of each, plus an API
# check of the Python binding. Uses python$PYTHON_VERSION (set by the image: 2.7 or 3.x).
set -u
py=python$PYTHON_VERSION
fail=0
work=$(mktemp -d)
cp -a "$TOSROOT/apps/RadioCountToLeds" "$TOSROOT/apps/BaseStation" "$work/"
noise="$TOSROOT/tos/lib/tossim/noise/meyer-heavy.txt"

run() {  # run <app> <make target> <test script> [args]
  local app=$1 target=$2 script=$3; shift 3
  echo "== $app: make micaz $target"
  # BUILD_EXTRA_DEPS= skips mig (message classes): not needed for the .so, and not yet
  # validated with nesC 1.4.0 (see README, "Not tested yet").
  if ! (cd "$work/$app" && make micaz "$target" BUILD_EXTRA_DEPS= > "$work/$app.build.log" 2>&1); then
    echo "BUILD FAIL"; tail -20 "$work/$app.build.log"; fail=1; return
  fi
  (cd "$work/$app" && $py "/tests/$script" "$@") || fail=1
}

gcc --version | head -1
nescc --version | head -1
$py --version

run RadioCountToLeds sim radio_count.py "$noise"
echo "== RadioCountToLeds: API check"
[ -f "$work/RadioCountToLeds/TOSSIM.py" ] && (cd "$work/RadioCountToLeds" && $py /tests/api_check.py) || fail=1
run BaseStation sim-sf sf_handshake.py

[ $fail -eq 0 ] && echo "ALL PASS" || echo "SOME FAILED"
exit $fail
