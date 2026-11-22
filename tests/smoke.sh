#!/bin/bash
# Runs inside the toolchain image:
#   podman run --rm -v ./tests:/tests:ro,Z tinyos-toolchain:<tag> bash /tests/smoke.sh
# Builds two stock TinyOS apps for TOSSIM and runs a short simulation of each, plus an API
# check of the Python binding. Uses python$PYTHON_VERSION (set by the image: 2.7 or 3.x).
# In images with AVR support (/usr/local/bin/avr-gcc), it also builds Blink and RadioCountToLeds
# for micaz, iris, mica2 and mica2dot, and runs the micaz builds on the Avrora simulator (Blink's LED
# periods; RadioCountToLeds on 2 nodes, packets received) when the image has `avrora`.
# Also there: the flash volume scripts (tos-storage-*), a Deluge app build and the Deluge tools
# with the Python SDK's tos module (deluge_check.py).
# Each build's generated C (app.c, normalized by gen_c_norm.awk: TinyOS and app code only)
# must match tests/ref/<app>-<target>.txt. To regenerate the references after an intended
# change, mount a writable dir and set GEN_C_UPDATE to it.
set -u
py=python$PYTHON_VERSION
fail=0
work=$(mktemp -d)
cp -a "$TOSROOT/apps/RadioCountToLeds" "$TOSROOT/apps/BaseStation" "$TOSROOT/apps/Blink" "$work/"
noise="$TOSROOT/tos/lib/tossim/noise/meyer-heavy.txt"
# mig (message classes) is tested in the Python 3 images; jammy-py2 (frozen) has neither the
# mig fixes nor tinyos.jar in CLASSPATH, and there the mig targets are skipped as before.
case "$PYTHON_VERSION" in 2.*) mig=0 ;; *) mig=1 ;; esac

run() {  # run <app> <make target> <test script> [args]
  local app=$1 target=$2 script=$3; shift 3
  echo "== $app: make micaz $target"
  # BUILD_EXTRA_DEPS= skips mig (the app's message classes), except for RadioCountToLeds
  # when the image supports it: mig_check.py tests those classes.
  local deps=BUILD_EXTRA_DEPS=
  [ "$app" = RadioCountToLeds ] && [ $mig = 1 ] && deps=
  # shellcheck disable=SC2086
  if ! (cd "$work/$app" && make micaz "$target" $deps > "$work/$app.build.log" 2>&1); then
    echo "BUILD FAIL"; tail -20 "$work/$app.build.log"; fail=1; return
  fi
  gen_c_check "$app-$target" "$work/$app/simbuild/micaz/app.c"
  (cd "$work/$app" && $py "/tests/$script" "$@") || fail=1
}

gen_c_check() {  # gen_c_check <reference name> <generated app.c> [build log]
  local norm="$work/$1.txt" ref="/tests/ref/$1.txt" uid=""
  # The build's random IDENT_UIDHASH (compiled in by Deluge apps), from the compiler's command
  # line in the build log.
  [ -n "${3:-}" ] && uid=$(grep -o 'IDENT_UIDHASH=0x[0-9a-fA-F]*L' "$3" | head -1 | cut -d= -f2)
  awk -v tosroot="$TOSROOT" -v uidhash="$uid" -f /tests/gen_c_norm.awk "$2" > "$norm"
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
# Fix 17: Terra's Makefile needs bc (Python 3 images; jammy-py2 is frozen without it).
if [ $mig = 1 ] && ! command -v bc > /dev/null; then echo "FAIL: bc missing (Terra's Makefile uses it)"; fail=1; fi
nescc --version | head -1
$py --version

run RadioCountToLeds sim radio_count.py "$noise"
echo "== RadioCountToLeds: API check"
[ -f "$work/RadioCountToLeds/TOSSIM.py" ] && (cd "$work/RadioCountToLeds" && $py /tests/api_check.py) || fail=1
echo "== RadioCountToLeds: mig message classes (Python, Java, delivered in TOSSIM)"
if [ $mig = 1 ]; then
  (cd "$work/RadioCountToLeds" && $py /tests/mig_check.py "$noise") || fail=1
else
  echo "skipped: Python 2 image (frozen, without the mig fixes)"
fi
run BaseStation sim-sf sf_handshake.py
echo "== BaseStation: Java MsgReader over the SerialForwarder (sf@localhost:9002)"
if [ $mig = 1 ]; then
  (cd "$work/BaseStation" && $py /tests/sf_java_check.py) || fail=1
else
  echo "skipped: Python 2 image (frozen, without tinyos.jar in CLASSPATH)"
fi

avr() {  # avr <app under apps/> <platform>: build for the mote, from a fresh copy of the app
  local app=$1 plat=$2 name="${1//\//_}-$2"
  local dir="$work/avr-$name"
  echo "== $app: make $plat"
  cp -a "$TOSROOT/apps/$app" "$dir"
  if ! (cd "$dir" && make "$plat" BUILD_EXTRA_DEPS= > build.log 2>&1); then
    echo "BUILD FAIL"; grep -v '^ ' "$dir/build.log" | tail -15; fail=1; return
  fi
  grep -E 'bytes in (ROM|RAM)' "$dir/build.log" | tr -s ' ' | tr '\n' ' '; echo
  gen_c_check "$name" "$dir/build/$plat/app.c" "$dir/build.log"
}

if [ -x /usr/local/bin/avr-gcc ]; then
  avr-gcc --version | head -1
  for app in Blink RadioCountToLeds; do
    for plat in micaz iris mica2 mica2dot; do avr "$app" "$plat"; done
  done
  # Flash volumes (fork commits 9b530d6, 5feb228): tos-storage-* run on Python 3 and keep the flash layout
  # of Python 2. tests/ref/storage holds the original scripts' output on Python 2.7.
  echo "== Flash volumes: tos-storage-at45db and -stm25p, layout as on Python 2"
  for x in tests/deluge/GoldenImage:at45db:micaz UDPEcho:at45db:micaz tests/deluge/GoldenImage:stm25p:telosb; do
    IFS=: read -r app chip plat <<< "$x"
    ref="/tests/ref/storage/${app//\//_}-$chip.h"
    if (cd "$TOSROOT/apps/$app" && tos-storage-$chip "$TOSROOT/tos/platforms/$plat" < "volumes-$chip.xml" 2>&1) \
        | diff -q "$ref" - > /dev/null; then
      echo "  same as tests/ref: $app ($chip)"
    else
      echo "  FAIL: $app ($chip) differs from $ref"; fail=1
    fi
  done
  # An app with flash volumes (Deluge: 4 volumes): its build runs tos-storage-at45db.
  avr tests/deluge/Blink micaz
  echo "== Deluge tools and the Python SDK's tos module (network@ and serial@)"
  (cd "$work/avr-tests_deluge_Blink-micaz" && $py /tests/deluge_check.py) || fail=1
  # make install's programmer call (dry run, make -n: no board here): avrdude with the MIB520
  # (USB) and the MIB600 (Ethernet, "eprb").
  echo "== make install: programmer command (dry run)"
  for prog in mib520,/dev/ttyUSB0 eprb,192.0.2.1; do
    cmd=$(cd "$work/avr-Blink-micaz" && make -n micaz reinstall,1 "$prog" 2>&1 | grep -E '^(avrdude|uisp) ')
    echo "  $prog: ${cmd:-(none)}" | cut -c1-110
    case "$cmd" in avrdude\ -cmib510\ *) ;; *) echo "FAIL: $prog should program with avrdude -cmib510"; fail=1 ;; esac
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
