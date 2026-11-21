#!/bin/bash
# Runs inside the toolchain image:
#   podman run --rm -v ./tests:/tests:ro,Z tinyos-toolchain:<tag> bash /tests/smoke.sh
# Builds two stock TinyOS apps for TOSSIM and runs a short simulation of each, plus an API
# check of the Python binding. Uses python$PYTHON_VERSION (set by the image: 2.7 or 3.x).
# In images with AVR support (/usr/local/bin/avr-gcc), it also builds Blink and RadioCountToLeds
# for micaz, iris and mica2, and runs the micaz builds on the Avrora simulator (Blink's LED
# periods; RadioCountToLeds on 2 nodes, packets received) when the image has `avrora`.
# Each build's generated C (app.c, normalized by gen_c_norm.awk: TinyOS and app code only)
# must match tests/ref/<app>-<target>.txt. To regenerate the references after an intended
# change, mount a writable dir and set GEN_C_UPDATE to it.
set -u
py=python$PYTHON_VERSION
fail=0
work=$(mktemp -d)
cp -a "$TOSROOT/apps/RadioCountToLeds" "$TOSROOT/apps/BaseStation" "$TOSROOT/apps/Blink" "$work/"
noise="$TOSROOT/tos/lib/tossim/noise/meyer-heavy.txt"

run() {  # run <app> <make target> <test script> [args]
  local app=$1 target=$2 script=$3; shift 3
  echo "== $app: make micaz $target"
  # BUILD_EXTRA_DEPS= skips mig (message classes): not needed for the .so, and not yet
  # validated with nesC 1.4.0 (see README, "Not tested yet").
  if ! (cd "$work/$app" && make micaz "$target" BUILD_EXTRA_DEPS= > "$work/$app.build.log" 2>&1); then
    echo "BUILD FAIL"; tail -20 "$work/$app.build.log"; fail=1; return
  fi
  gen_c_check "$app-$target" "$work/$app/simbuild/micaz/app.c"
  (cd "$work/$app" && $py "/tests/$script" "$@") || fail=1
}

gen_c_check() {  # gen_c_check <reference name> <generated app.c>
  local norm="$work/$1.txt" ref="/tests/ref/$1.txt"
  awk -v tosroot="$TOSROOT" -f /tests/gen_c_norm.awk "$2" > "$norm"
  if [ -n "${GEN_C_UPDATE:-}" ]; then
    cp "$norm" "$GEN_C_UPDATE/" && echo "generated C: reference written to $GEN_C_UPDATE"
  elif diff -q "$ref" "$norm" > /dev/null; then
    echo "generated C: same as tests/ref ($(wc -l < "$norm") lines)"
  else
    echo "generated C: DIFFERS from tests/ref/$1.txt. Changed code comes from:"
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

avr() {  # avr <app> <platform>: build for the mote, from a fresh copy of the app
  local app=$1 plat=$2 dir="$work/avr-$1-$2"
  echo "== $app: make $plat"
  cp -a "$TOSROOT/apps/$app" "$dir"
  if ! (cd "$dir" && make "$plat" BUILD_EXTRA_DEPS= > build.log 2>&1); then
    echo "BUILD FAIL"; grep -v '^ ' "$dir/build.log" | tail -15; fail=1; return
  fi
  grep -E 'bytes in (ROM|RAM)' "$dir/build.log" | tr -s ' ' | tr '\n' ' '; echo
  gen_c_check "$app-$plat" "$dir/build/$plat/app.c"
}

if [ -x /usr/local/bin/avr-gcc ]; then
  avr-gcc --version | head -1
  for app in Blink RadioCountToLeds; do
    for plat in micaz iris mica2; do avr "$app" "$plat"; done
  done
  if command -v avrora > /dev/null; then
    echo "== Blink micaz on Avrora: 4 s"
    avrora -platform=micaz -input=elf -seconds=4 -monitors=leds -colors=false \
      "$work/avr-Blink-micaz/build/micaz/main.exe" > "$work/avrora-blink.txt" 2>&1
    python3 /tests/avrora_check.py blink "$work/avrora-blink.txt" || fail=1
    echo "== RadioCountToLeds micaz on Avrora: 2 nodes, 3 s"
    avrora -simulation=sensor-network -platform=micaz -input=elf -nodecount=2 -seconds=3 \
      -monitors=packet -colors=false "$work/avr-RadioCountToLeds-micaz/build/micaz/main.exe" \
      > "$work/avrora-radio.txt" 2>&1
    python3 /tests/avrora_check.py radio "$work/avrora-radio.txt" 5 || fail=1
  fi
else
  echo "== AVR: skipped (no AVR support in this image)"
fi

[ $fail -eq 0 ] && echo "ALL PASS" || echo "SOME FAILED"
exit $fail
