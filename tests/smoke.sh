#!/bin/bash
# Runs inside the toolchain image:
#   podman run --rm -v ./tests:/tests:ro,Z tinyos-toolchain:2.1.2-jammy-py2 bash /tests/smoke.sh
# Builds two stock TinyOS apps for TOSSIM and runs a short simulation of each.
set -u
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
  (cd "$work/$app" && python2.7 "/tests/$script" "$@") || fail=1
}

gcc --version | head -1
nescc --version | head -1
python2.7 --version

run RadioCountToLeds sim radio_count.py "$noise"
run BaseStation sim-sf sf_handshake.py

[ $fail -eq 0 ] && echo "ALL PASS" || echo "SOME FAILED"
exit $fail
