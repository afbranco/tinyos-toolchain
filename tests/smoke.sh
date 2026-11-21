#!/bin/bash
# Runs inside the toolchain image:
#   podman run --rm -v ./tests:/tests:ro,Z tinyos-toolchain:<tag> bash /tests/smoke.sh
# Builds two stock TinyOS apps for TOSSIM and runs a short simulation of each, plus an API
# check of the Python binding. Uses python$PYTHON_VERSION (set by the image: 2.7 or 3.x).
# Each build's generated C (simbuild/micaz/app.c, normalized by gen_c_norm.awk: TinyOS and
# app code only) must match tests/ref/<app>-<target>.txt. To regenerate the references after
# an intended change, mount a writable dir and set GEN_C_UPDATE to it.
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
  gen_c_check "$app" "$target"
  (cd "$work/$app" && $py "/tests/$script" "$@") || fail=1
}

gen_c_check() {  # gen_c_check <app> <make target>
  local norm="$work/$1-$2.txt" ref="/tests/ref/$1-$2.txt"
  awk -v tosroot="$TOSROOT" -f /tests/gen_c_norm.awk "$work/$1/simbuild/micaz/app.c" > "$norm"
  if [ -n "${GEN_C_UPDATE:-}" ]; then
    cp "$norm" "$GEN_C_UPDATE/" && echo "generated C: reference written to $GEN_C_UPDATE"
  elif diff -q "$ref" "$norm" > /dev/null; then
    echo "generated C: same as tests/ref ($(wc -l < "$norm") lines)"
  else
    echo "generated C: DIFFERS from tests/ref/$1-$2.txt. Changed code comes from:"
    # For each changed hunk, the last "@@ <file>" line before it in the new output.
    diff "$ref" "$norm" | sed -n 's/^[0-9,]*[acd]\([0-9]*\).*/\1/p' | while read -r n; do
      awk -v n="$n" 'NR <= n && /^@@ / { f = $2 } NR == n { print "  " f; exit }' "$norm"
    done | sort | uniq -c
    diff "$ref" "$norm" | head -30; fail=1
  fi
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
