# tinyos-toolchain

Build **TinyOS 2.1.2 and its simulator, TOSSIM, on a current Linux** (64-bit), as a container
image. The original toolchain only builds on Ubuntu 12.04 (GCC 4.6, nesC 1.3.x, 32-bit Python
2.7). This project brings it to a maintained environment, one step at a time, **without changing
TinyOS itself** unless a step requires it.

The first consumer is [Terra](https://github.com/afbranco/Terra), whose VM runs on TOSSIM, and
through it the [TerraSim](https://github.com/afbranco/TerraSim) classroom simulator. Nothing here
depends on Terra: the tests use stock TinyOS apps.

## Status

| Image tag | Base | Python | `make micaz sim` | `make micaz sim-sf` |
|---|---|---|---|---|
| `2.1.2-jammy-py2` | Ubuntu 22.04, x86_64 | 2.7 | ✅ | ✅ |
| `2.1.2-jammy-py3` | Ubuntu 22.04, x86_64 | 3.10 | ✅ | ✅ |
| `2.1.2-resolute-py3` | Ubuntu 26.04, x86_64 | 3.14 | ✅ | ✅ |

Ubuntu 22.04 is the **last** Ubuntu that ships Python 2.7, and its standard support ends in April
2027. `jammy-py2` is a bridge, not a destination. `resolute-py3` (Ubuntu 26.04 LTS, supported
until 2031) is the long-term one; `jammy-py3` stays as the closest Python 3 image to the old
toolchain (same compiler as `jammy-py2`).

## Quick start

```bash
podman build -t tinyos-toolchain:2.1.2-resolute-py3 -f resolute-py3/Containerfile .
podman run --rm -v ./tests:/tests:ro,Z tinyos-toolchain:2.1.2-resolute-py3 bash /tests/smoke.sh
```

Building an app of your own:

```bash
podman run --rm -it -v ./myapp:/work:Z tinyos-toolchain:2.1.2-resolute-py3 make micaz sim-sf
```

Sources are fetched at fixed versions, checked by SHA-256:
[tinyos/nesc](https://github.com/tinyos/nesc) at `v1.4.0` (both images), and TinyOS from
[tinyos/tinyos-main](https://github.com/tinyos/tinyos-main) at `release_tinyos_2_1_2`
(`jammy-py2`) or from the `tossim-py3` branch of
[afbranco/tinyos-main](https://github.com/afbranco/tinyos-main/tree/tossim-py3) (`*-py3`):
the same tag plus one commit, described below. The official repositories are archived
(read-only).

## The eight fixes

Each one was hit, in this order, while building `RadioCountToLeds` and `BaseStation` for TOSSIM
on Ubuntu 22.04 with Python 2.7. None of them edits a TinyOS file. `jammy-py3` applies the same
fixes, with `python-is-python3` for fix 1 and `PYTHON_VERSION=3.10` for fix 7.

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

## Python 3

Python 3 needs new TOSSIM bindings, so this is the one step that changes TinyOS. The change is a
single commit on top of `release_tinyos_2_1_2`, on the
[`tossim-py3`](https://github.com/afbranco/tinyos-main/tree/tossim-py3) branch of
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
  packet tools) is Python 2 code and is **not** ported; `jammy-py3` does not put it on
  `PYTHONPATH`. TOSSIM itself does not need it: `Tossim([])` works, and so does `Tossim()` with
  a hand-written variable list.

## Known issues (also in the original TinyOS 2.1.2)

- **`removeChannel()` does nothing.** `sim_log_remove_channel` never rebuilds the output table
  (`sim_log_commit_change`) and always returns `True`. Do not close a file that TOSSIM still
  writes to.
- **Runs are not repeatable by default**: the random seed comes from the clock
  (`gettimeofday`). Call `t.randomSeed(n)` to fix it.

## Tests

`tests/smoke.sh` runs with the image's Python (`python$PYTHON_VERSION`). It builds two stock
apps and runs them:

- **RadioCountToLeds**, `make micaz sim`: 2 motes for 20 simulated seconds; passes if simulated
  time reaches 20 s and mote 2 receives packets.
- **BaseStation**, `make micaz sim-sf`: boots 2 motes and checks the SerialForwarder handshake
  (`"U "`) on TCP port 9002.
- **API check** (`tests/api_check.py`, on the RadioCountToLeds build): `getVariable()` through
  the variable list, `setData()`/`data()` with binary bytes, and a file added twice to a
  channel getting each line once. Each check was seen to fail with its part of the binding
  change undone.

A smoke test proves the build works, not that it **simulates the same** as the old 32-bit
build. Equivalence needs a trace comparison against the original toolchain (see Roadmap).

## Not tested yet

- `mig` (message classes for Java/Python) with nesC 1.4.0. The tests skip it with
  `BUILD_EXTRA_DEPS=`; it is not needed for the TOSSIM `.so`.
- Mote targets (real hardware). Out of scope for now.

## Roadmap

1. ~~**Python 3**~~: done in `jammy-py3` (see "Python 3").
2. ~~**A current Ubuntu**~~: done in `resolute-py3` (26.04 LTS).
3. **Equivalence oracle**: same program, same seed, old toolchain vs new, identical event traces.
