# tinyos-toolchain

Build **TinyOS 2.1.2 and its simulator, TOSSIM, on a current Linux** (64-bit), as a container
image. The original toolchain only builds on Ubuntu 12.04 (GCC 4.6, nesC 1.3.x, 32-bit Python
2.7). This project brings it to a maintained environment, one step at a time, **without changing
TinyOS itself** unless a step requires it.

The first consumer is [Terra](https://github.com/afbranco/Terra), whose VM runs on TOSSIM, and
through it the [TerraSim](https://github.com/afbranco/TerraSim) classroom simulator. Nothing here
depends on Terra: the tests use stock TinyOS apps.

## Scope

- **Supported: TOSSIM** (`make micaz sim` and `make micaz sim-sf`), which is what Terra needs.
  This is what the images build and the tests check.
- **Time-boxed: AVR motes** (micaz, iris, mica2, mica2dot). `resolute-py3` builds them (fixes 12, 13
  and one upstream TinyOS commit), and the micaz firmware runs on the
  [Avrora](https://sourceforge.net/projects/avrora/) simulator in the tests. Not yet tried on a
  real mote. It stays only if each fix stays small; otherwise it is dropped and the reason
  written here.
- **Out of scope:** the other TinyOS 2.1.2 platforms (MSP430, ARM, XScale, M16C). Their old
  compilers are gone (for MSP430, TI's current `msp430-elf` GCC is not compatible with the
  mspgcc TinyOS was written for), so supporting them means porting TinyOS, not building it.

## Status

| Image tag | Base | Python | `make micaz sim` | `make micaz sim-sf` | `make micaz` / `iris` / `mica2` / `mica2dot` | |
|---|---|---|---|---|---|---|
| `2.1.2-resolute-py3` | Ubuntu 26.04, x86_64 | 3.14 | ✅ | ✅ | ✅ (micaz also on Avrora) | **maintained** |
| `2.1.2-jammy-py2` | Ubuntu 22.04, x86_64 | 2.7 | ✅ | ✅ | | frozen |

`resolute-py3` (Ubuntu 26.04 LTS, supported until 2031) is the one image that gets new work.
`jammy-py2` is **frozen**: kept, unchanged, as a bridge for Python 2 code and as the reference
closest to the old toolchain. Ubuntu 22.04 is the last Ubuntu with Python 2.7, and its standard
support ends in April 2027. (A `jammy-py3` image existed for the Python 3 step; it was removed
once `resolute-py3` passed, and is in the git history.)

## Quick start

Published images (built and tested by GitHub Actions on every push to `main`, see
`.github/workflows/images.yml`):

```bash
podman pull ghcr.io/afbranco/tinyos-toolchain:2.1.2-resolute-py3          # latest build
podman pull ghcr.io/afbranco/tinyos-toolchain:2.1.2-resolute-py3-<commit> # one exact build
```

A tag is published only if `tests/smoke.sh` gives `ALL PASS` in that image. Projects that
must not change under them (Terra's releases) should use the `-<commit>` tag.

Or build locally:

```bash
podman build -t tinyos-toolchain:2.1.2-resolute-py3 -f resolute-py3/Containerfile .
podman run --rm -v ./tests:/tests:ro,Z tinyos-toolchain:2.1.2-resolute-py3 bash /tests/smoke.sh
```

Building an app of your own:

```bash
podman run --rm -it -v ./myapp:/work:Z ghcr.io/afbranco/tinyos-toolchain:2.1.2-resolute-py3 make micaz sim-sf
```

Sources are fetched at fixed versions, checked by SHA-256:
[tinyos/nesc](https://github.com/tinyos/nesc) at `v1.4.0`, and TinyOS from
[tinyos/tinyos-main](https://github.com/tinyos/tinyos-main) at `release_tinyos_2_1_2`
(`jammy-py2`) or from the `2.1.2-maintained` branch of
[afbranco/tinyos-main](https://github.com/afbranco/tinyos-main/tree/2.1.2-maintained) (`*-py3`):
the same tag plus a few commits, listed in "TinyOS changes". The official repositories are archived
(read-only).

## The eight fixes

Each one was hit, in this order, while building `RadioCountToLeds` and `BaseStation` for TOSSIM
on Ubuntu 22.04 with Python 2.7. None of them edits a TinyOS file. `resolute-py3` applies them
too, with `python-is-python3` for fix 1, `PYTHON_VERSION=3.14` for fix 7, and fix 11 instead of
fix 6.

| # | Symptom | Cause | Fix |
|---|---|---|---|
| 1 | tools `configure`: `I can't find python` | 22.04 has `python2.7`, not `python` | symlink `python`, `python2` → `python2.7` |
| 2 | tools `configure`: `java not found` | the tools build includes the Java SDK part | `openjdk-11-jdk-headless` |
| 3 | `mig`: `Couldn't execute avr-gcc` | `mig -target=micaz` uses the AVR compiler to lay out message structs, even for the simulator | `gcc-avr`, `avr-libc` |
| 4 | `nesC: Internal error` | the `nescc` 1.3.5 package (2013) vs GCC 11 / glibc 2.35 | nesC **1.4.0** built from source (needs `emacs`, `bison`, `flex`, `gperf`: building from git generates parser code) |
| 5 | `syntax error before '__value'` in `mathcalls-helper-functions.h` | nesC does not know glibc's `_Float32` … `_Float128` | map them to `float` / `double` / `long double`, **in `PFLAGS` only** (nesC step); in `CFLAGS` they break the C++ wrapper |
| 6 | `'fclose' undeclared` in `stdio.h` | with GCC ≥ 11, glibc tags `fopen` with `__attr_dealloc(fclose)`, and nesC's generated C declares `fclose` later | compile with **GCC 10** (same apt) |
| 7 | `Python.h: No such file` | `sim.extra` turns `Python 2.7.18` into `2.78` (its `sed` expects a one-digit patch) | `PYTHON_VERSION=2.7` |
| 8 | `undefined symbol: __nesc_atomic_end` on import | GCC ≥ 5 defaults to C99 `inline`: a non-static inline function emits no code | `-fgnu89-inline` |

## Ubuntu 26.04: three more fixes

26.04 has GCC 15 and no GCC 10, so fix 6 has to be done another way, and GCC 15's default
dialect (C23) is new to nesC. Still no TinyOS file is edited.

| # | Symptom | Cause | Fix |
|---|---|---|---|
| 9 | building nesC: `incompatible pointer type 'const unsigned int *'` in `libcpp/directives.c` | nesC's libcpp writes `U"string"` meaning its macro `U` = `(const unsigned char *)`; since C11 that is a UTF-32 literal, and GCC 14 made the mismatch an error. (Older GCCs only warned, so those few strings were already UTF-32 in builds with C11 or later defaults.) | build nesC with `CFLAGS="-g -O2 -std=gnu89"`, its dialect |
| 10 | `` `nullptr' undeclared `` in `stddef.h`, `implicit declaration of function '_Generic'` | GCC 15 defaults to C23: its headers use `nullptr`, glibc 2.43 makes `strrchr` & co. `_Generic` macros, and nesC parses neither. nesC forwards only `-m` options to gcc, so `PFLAGS` cannot set the dialect | a `gcc` wrapper (`resolute-py3/gcc`, installed as `/usr/local/bin/gcc`) adds `-std=gnu17` |
| 11 | `'fclose' undeclared` in `stdio.h` (fix 6 again) | same cause as fix 6: nesC drops the unused `fclose` declaration but keeps `__attr_dealloc(fclose)` on `fopen` & co. | the same wrapper reports GCC 10 **only** to nesC's predefined-macro query (`gcc -E -dM`), so nesC sees the headers as with GCC 10. The generated C is compiled by GCC 15 |

The `x86_64-linux-gnu-gcc` used by Python extension builds is not affected by the wrapper.

## AVR motes: three more fixes and one upstream commit

| # | Symptom | Cause | Fix |
|---|---|---|---|
| 12 | `` `ASSR' undeclared ``, `WDT`, `RAMPZ`… (registers missing) | since avr-gcc 5 the driver reads a per-device specs file and gives the compiler (here nesC) `-mmcu=avr51` instead of `-mmcu=atmega128`; nesC reads the predefined macros for that architecture, so `__AVR_ATmega128__` & co. are missing and `<avr/io.h>` selects no device | an `avr-gcc` wrapper (`resolute-py3/avr-gcc`, as `/usr/local/bin/avr-gcc`): for nesC's call only, it passes the macros that `-mmcu=<device>` defines and its architecture does not (for atmega128: `__AVR_ATmega128__`, `__AVR_DEVICE_NAME__`, `__AVR_RODATA_IN_RAM__`) |
| 13 | `syntax error before 'pgm_read_i24'` in `avr/pgmspace.h` | avr-gcc 14 defines `__INT24_MAX__`, and avr-libc then declares functions on `__int24`, a type nesC does not know | the same wrapper undefines `__INT24_MAX__` for nesC (TinyOS does not use those functions) |
| 14 | `make micaz install` fails: `uisp: No such file`, and Ubuntu's `uisp` has no `-dprog=mib510` | TinyOS used its own patched `uisp` | `PROGRAMMER=avrdude` in the image's environment: TinyOS's rules pick avrdude (`-cmib510`) |
| – | `must be const in order to be put into read-only section by means of '__attribute__((progmem))'` | TinyOS 2.1.2's `PROGMEM` typedefs drop `const`, which newer GCCs require | upstream commit [`cbbddf66`](https://github.com/tinyos/tinyos-main/commit/cbbddf66ee8acbbc87fe316e7077cc1144968d88) (2014), cherry-picked into the fork |

The image also has **Avrora** 1.7.117 (2013, BSD, vendored in `third_party/avrora`; `avrora`
command), an AVR simulator for micaz
and mica2, run on **JDK 17**: Avrora uses `java.lang.Compiler`, which Java 21 removed. Example:

```bash
avrora -platform=micaz -input=elf -seconds=4 -monitors=leds build/micaz/main.exe
avrora -simulation=sensor-network -platform=micaz -input=elf -nodecount=2 -seconds=3 -monitors=packet build/micaz/main.exe
```

### Programming a mote

TinyOS 2.1.2 programs micaz, mica2 and mica2dot with `uisp`, but a version patched and shipped
by TinyOS: Ubuntu's `uisp` (20050207) has neither the MIB510/MIB520 nor the MIB600 support. The
image has **avrdude** 7.1 instead and sets `PROGRAMMER=avrdude` (fix 14): TinyOS's make rules
already have its options for every AVR platform, and iris used it by default. The container sees the programming board
only if it is passed in. Examples, node ID 1:

```bash
# MIB520 (USB): it shows two serial ports; programming uses the first one.
podman run --rm -it --device /dev/ttyUSB0 -v ./myapp:/work:Z \
  tinyos-toolchain:2.1.2-resolute-py3 make micaz install,1 mib520,/dev/ttyUSB0

# MIB510 (serial, or through a USB-serial adapter): same, with mib510,<port>.
# MIB600 (Ethernet, "eprb" in TinyOS): no --device, just the board's address.
podman run --rm -it -v ./myapp:/work:Z \
  tinyos-toolchain:2.1.2-resolute-py3 make micaz install,1 eprb,<board address>
```

On the host, the user needs access to the port (on Ubuntu: the `dialout` group); with rootless
podman, also `--group-add keep-groups`. In Blink, `make install` warns that it could not find
`TOS_NODE_ID`: Blink does not use the ID, so the compiler removed it, as with the old toolchain.

`cbbddf66` also edits `tos/chips/atm128/sim/atm128const.h`, which TOSSIM includes: the
generated-C test shows no change in the TOSSIM builds (those typedefs are only used by
mote-only code: `McuSleepC`, the CC1000 radio).

## mig: three more fixes and one TinyOS commit

`mig` generates an app's message classes (Java, Python) from its nesC structs; apps list them
in `BUILD_EXTRA_DEPS` (RadioCountToLeds: `RadioCountMsg.class`, `RadioCountMsg.py`).

| # | Symptom | Cause | Fix |
|---|---|---|---|
| 15 | `javac RadioCountMsg.java`: `package net.tinyos.message does not exist` | the generated Java class needs TinyOS's `tinyos.jar`, which TinyOS's own environment put in `CLASSPATH` | `CLASSPATH=$TOSROOT/support/sdk/java/tinyos.jar:.` in the image |
| 16 | the Python class's `offset_<field>()` / `size_<field>()` give `2.0`, not `2`, in Python 3 | nesC's generator (`genpython.pm`) writes `(bits / 8)` | `//` instead, in the image (a `sed` on nesC's installed file, checked) |
| 17 | Terra's `make micaz ...`: `bc: not found`, then mig `syntax error before ','` in Terra's headers | Terra's Makefile computes node IDs and memory sizes with `bc` (installed by default on the old Ubuntu, not in a container) and passes them as macros, empty without it | `bc` in the image |
| – | the Python class's first `set_<field>()`: `can only concatenate str (not "bytes") to str` | `tinyos.message.Message`, the base class from TinyOS's Python SDK, makes its buffer with `chr(0) * n` (a `str` in Python 3) | fork commit `0dca1d8`: `b"\0" * n` (the same in Python 2) |

With them, the Python class works in Python 3 with `bytes`, like TOSSIM's `Packet.setData()`
and `data()`, so a message built with it can be delivered to a mote in TOSSIM (see "Tests"). It
needs `$TOSROOT/support/sdk/python` on `sys.path` (not set in the image, as the rest of that
SDK is still Python 2 only). `jammy-py2` (frozen) has neither fix.

**Terra:** with `bc`, Terra's public TerraVM builds for micaz in the image
(`make micaz VM:GRP TYPE:NOBS QUEUE:SHORT`), and the six Java message classes its Makefile
generates with mig are **identical, byte for byte**, to the ones committed in the Terra
repository (made with the old toolchain); they compile against `tinyos.jar`.

**Java and the serial port:** TinyOS's Java tools (SerialForwarder, MsgReader, `MoteIF`) use
a JNI library, `libtoscomm`, for serial ports. The image does not build it: `tinyos.jar`
carries a prebuilt copy (`linux_amd64_toscomm.lib`), which the Java SDK extracts and loads
(it prints "Could not load library 'toscomm'" first, then "Library loaded successfully"); it
loads with the current glibc. (Building it from `tools/tinyos/java` would fail: it includes
`<termio.h>`, gone from glibc, but it also includes `<termios.h>`, so that line can go.) A
real serial port is still to be tried with a mote: a pseudo-terminal cannot stand in, as
`libtoscomm` asks for the modem lines' status, which a pseudo-terminal does not have.

## TinyOS changes

All on the [`2.1.2-maintained`](https://github.com/afbranco/tinyos-main/tree/2.1.2-maintained)
branch of afbranco/tinyos-main, on top of `release_tinyos_2_1_2`, one commit per change:

| Commit | What | Origin |
|---|---|---|
| `da2f9d0` | TOSSIM Python 3 bindings (SWIG 4), see "Python 3" | this project |
| `fc2953f` | AVR progmem consts with newer GCC | upstream `cbbddf66`, cherry-picked (`-x`), author kept |
| `0dca1d8` | Python SDK `Message`: buffer as `bytes`, for mig's Python classes in Python 3 | this project |

## Python 3

Python 3 needs new TOSSIM bindings: a single commit (`da2f9d0`) on top of `release_tinyos_2_1_2`, on the
[`2.1.2-maintained`](https://github.com/afbranco/tinyos-main/tree/2.1.2-maintained) branch of
afbranco/tinyos-main. The wrappers (`tossim_wrap.cxx`, `TOSSIM.py`, in `tos/lib/tossim` and
`tos/lib/tossim/sf`) are regenerated with **SWIG 4.0.2** and committed, so the image does not
need SWIG. The same sources still build for Python 2.7 (the tests pass on both).

What changes for a user of the Python API:

- **The module is `_TOSSIM.so`**, not `_TOSSIMmodule.so`: Python 3 does not import
  `<name>module.so`. Anything that ships or copies the `.so` must use the new name.
- **`Packet.setData()` / `SerialPacket.setData()` take `bytes`**, and `data()` returns `bytes`
  of `length()`. (Python 2 keeps the old behaviour: a `str`, cut at the first zero byte.)
- **`addChannel(name, file)`** takes any Python file with a descriptor. The binding keeps one
  `FILE*` per descriptor, so a file added to several channels still gets each line once.
- **`getVariable()`** returns `int` / `float`, or `bytes` for raw memory; the variable list given
  to `Tossim()` uses `str`.
- **The TinyOS Python SDK** (`support/sdk/python`: `tinyos.tossim.TossimApp`, `NescApp`, the
  packet tools) is Python 2 code and is **not** ported, except `tinyos.message.Message`, the base
  of mig's Python classes (see "mig"); `resolute-py3` does not put it on
  `PYTHONPATH`. TOSSIM itself does not need it: `Tossim([])` works, and so does `Tossim()` with
  a hand-written variable list.

## 64-bit hosts

TOSSIM compiles the mote code for the host, so type sizes change: `int` is 16 bits on a micaz
and 32 in TOSSIM (as it always was), and on x86_64 `long` and pointers become 64 bits (32 on
the old i386 builds). Code that keeps a pointer in an integer, or relies on a 32-bit `long`,
can break. For the stock apps here, GCC reports **no pointer/integer size conversion** in the
TOSSIM builds (nesC's C and the C++ TOSSIM library). Application code (e.g. the Terra VM)
has to be checked on its own, and the equivalence oracle (see Roadmap) is the final test.

## Known issues (also in the original TinyOS 2.1.2)

- **`removeChannel()` does nothing.** `sim_log_remove_channel` never rebuilds the output table
  (`sim_log_commit_change`) and always returns `True`. Do not close a file that TOSSIM still
  writes to.
- **`Tossim::getNode()`** (`tos/lib/tossim/sf/tossim.c`) can reach the end without `return`
  (GCC: `control reaches end of non-void function`).
- **Runs are not repeatable by default**: the random seed comes from the clock
  (`gettimeofday`). Call `t.randomSeed(n)` to fix it.

## Tests

`tests/smoke.sh` runs with the image's Python (`python$PYTHON_VERSION`). It builds two stock
apps and runs them:

- **RadioCountToLeds**, `make micaz sim`: 2 motes for 20 simulated seconds; passes if simulated
  time reaches 20 s and mote 2 receives packets.
- **BaseStation**, `make micaz sim-sf`: boots 2 motes and checks the SerialForwarder handshake
  (`"U "`) on TCP port 9002.
- **mig** (`tests/mig_check.py`, on the RadioCountToLeds build, which now includes its mig
  targets; skipped in `jammy-py2`): the Python class sets a 16-bit counter as the bytes `12 34`
  (`bytes` in Python 3, integer offsets and sizes); the Java class gives the same bytes; and two
  messages built by the Python class, counters 5 and 2, are delivered to a TOSSIM mote, whose
  LEDs must show their low 3 bits (on off on, then off on off). Seen to fail without the fixes.
- **Java over the SerialForwarder** (`tests/sf_java_check.py`, on the BaseStation `sim-sf`
  build; skipped in `jammy-py2`): RadioCountMsg packets delivered over the radio to a
  BaseStation mote must reach TinyOS's Java `MsgReader`, connected with `-comm sf@localhost:9002`,
  decoded by the mig Java class (the path of Terra's TerraControl). Seen to fail with the
  wrong AM type.
- **API check** (`tests/api_check.py`, on the RadioCountToLeds build): `getVariable()` through
  the variable list, `setData()`/`data()` with binary bytes, and a file added twice to a
  channel getting each line once. Each check was seen to fail with its part of the binding
  change undone.
- **Generated C** (every build): nesC's output for the app (`simbuild/micaz/app.c`) is
  normalized by `tests/gen_c_norm.awk` and must match `tests/ref/<app>-<target>.txt`. The
  normalization keeps only code from TinyOS and the app (system headers change with every apt
  update), so this checks that a toolchain or fork change did not change the code being
  simulated. On a difference it lists the source files the changed code comes from. Today the
  references match in both images: the official TinyOS (`jammy-py2`, GCC 10) and the
  `2.1.2-maintained` fork with GCC 15 (`resolute-py3`) generate the same code. After an intended
  change, regenerate the references with `GEN_C_UPDATE=<writable dir>` and commit them with it.
- **AVR** (`resolute-py3` only): Blink and RadioCountToLeds built for micaz, iris, mica2 and mica2dot,
  each with its generated-C reference. Then, on Avrora (`tests/avrora_check.py`): Blink on a
  micaz for 4 s, whose three LEDs must toggle exactly every 1800000, 3600000 and 7200000
  cycles (250, 500 and 1000 TinyOS ms at 7.3728 MHz); and RadioCountToLeds on 2 micaz for
  3 s, each receiving at least 5 packets with no corrupted byte. Both checks were seen to
  fail with Blink's timer at 251 ms and with RadioCountToLeds not sending.

A smoke test proves the build works, not that it **simulates the same** as the old 32-bit
build. Equivalence needs a trace comparison against the original toolchain (see Roadmap).

## Not tested yet

- `mig` for other apps than RadioCountToLeds (struct arrays, strings) and its C output.
- Real motes, and `make install` with the MIB520 and MIB600 boards (to try on micaz, mica2 and
  mica2dot); the Java SerialForwarder on a real serial port (`-comm serial@/dev/ttyUSB1:micaz`).

## Roadmap

1. ~~**Python 3**~~: done (see "Python 3").
2. ~~**A current Ubuntu**~~: done in `resolute-py3` (26.04 LTS).
3. ~~**AVR motes**~~: build and Avrora (see "Scope"); a real mote is still to be tried.
4. **Equivalence oracle**: same program, same seed, old toolchain vs new, identical event traces.
