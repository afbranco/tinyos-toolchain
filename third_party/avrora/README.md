# Avrora 1.7.117 (vendored)

`avrora-beta-1.7.117.jar`: the [Avrora](https://sourceforge.net/projects/avrora/) AVR simulator
(UCLA Compilers Group), release of 2013-08-21, unchanged. BSD license: `LICENSE.txt`.

- **Origin:** `https://downloads.sourceforge.net/project/avrora/avrora-beta-1.7.117.jar`,
  SHA-256 `fd72eb0a23377550bb48d8f0f84cec218a02fd769ac586999c57f52ae219c060` (checked again by
  `resolute-py3/Containerfile`).
- **Why it is here:** SourceForge's download redirect sometimes lands on a mirror that does not
  answer, which made image builds fail. The jar is small (1.6 MB) and the license allows
  redistribution with the notice.
- **License text:** the jar does not include it, and SourceForge's CVS no longer serves the
  sources. `LICENSE.txt` is the `license.txt` of the CVS import at
  [github.com/33d/avrora](https://github.com/33d/avrora) (from
  `:pserver:anonymous@avrora.cvs.sourceforge.net`).
- Needs **Java 17** or older: it uses `java.lang.Compiler`, which Java 21 removed.
