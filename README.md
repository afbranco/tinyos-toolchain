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
| `2.1.2-*-py3` (next) | Ubuntu 22.04 or 24.04 | 3.x | | |

Ubuntu 22.04 is the **last** Ubuntu that ships Python 2.7, and its standard support ends in April
2027. `jammy-py2` is a bridge, not a destination: the next milestone is Python 3.

## Quick start

```bash
podman build -t tinyos-toolchain:2.1.2-jammy-py2 -f jammy-py2/Containerfile .
podman run --rm -v ./tests:/tests:ro,Z tinyos-toolchain:2.1.2-jammy-py2 bash /tests/smoke.sh
```

Building an app of your own:

```bash
podman run --rm -it -v ./myapp:/work:Z tinyos-toolchain:2.1.2-jammy-py2 make micaz sim-sf
```

Sources are fetched from the official repositories at fixed tags, checked by SHA-256:
[tinyos/tinyos-main](https://github.com/tinyos/tinyos-main) at `release_tinyos_2_1_2` and
[tinyos/nesc](https://github.com/tinyos/nesc) at `v1.4.0`. Both repositories are archived
(read-only).

## The eight fixes

Each one was hit, in this order, while building `RadioCountToLeds` and `BaseStation` for TOSSIM
on Ubuntu 22.04. None of them edits a TinyOS file.

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

## Tests

`tests/smoke.sh` builds two stock apps and runs them:

- **RadioCountToLeds**, `make micaz sim`: 2 motes for 20 simulated seconds; passes if simulated
  time reaches 20 s and mote 2 receives packets.
- **BaseStation**, `make micaz sim-sf`: boots 2 motes and checks the SerialForwarder handshake
  (`"U "`) on TCP port 9002.

A smoke test proves the build works, not that it **simulates the same** as the old 32-bit
build. Equivalence needs a trace comparison against the original toolchain (see Roadmap).

## Not tested yet

- `mig` (message classes for Java/Python) with nesC 1.4.0. The tests skip it with
  `BUILD_EXTRA_DEPS=`; it is not needed for the TOSSIM `.so`.
- Mote targets (real hardware). Out of scope for now.

## Roadmap

1. **Python 3.** Regenerate the TOSSIM bindings with SWIG 4 from the interface files already in
   the tree (`tos/lib/tossim/tossim.i`, `sf/SerialForwarder.i`, `sf/Throttle.i`). This is the
   first step that changes TinyOS files: it will live on a branch of
   [afbranco/tinyos-main](https://github.com/afbranco/tinyos-main) created **from the
   `release_tinyos_2_1_2` tag**, and this toolchain will point at it.
2. **Ubuntu 24.04**, once Python 2 is gone (nesC 1.4.0 already builds from source).
3. **Equivalence oracle**: same program, same seed, old toolchain vs new, identical event traces.
