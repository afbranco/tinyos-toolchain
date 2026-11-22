# The Deluge tools and the Python SDK's tos module (tos.py) on Python 3, run by smoke.sh in
# the micaz build of apps/tests/deluge/Blink:
#   python deluge_check.py
# 1. tos-build-deluge-image turns build/micaz/tos_image.xml into a Deluge image.
# 2. tos-deluge -p (ping) over TCP (network@, as with a MIB600) against fakemote.py, a fake
#    Deluge base station holding that image: it must read the image's ident back.
# 3. tos-dump.py over a serial port (serial@ on a pty, through pySerial) must print the
#    packets a fake mote sends: a printf message and bytes that need HDLC escaping.
from __future__ import print_function
import os, subprocess, sys, threading, time

sys.path.insert(0, "/tests")
from fakemote import am, crc16

py = sys.executable
fail = []


def check(ok, what):
    print("  %s: %s" % ("ok" if ok else "FAIL", what))
    if not ok:
        fail.append(what)


# 1. Deluge image
p = subprocess.Popen([py, "/usr/local/bin/tos-build-deluge-image", "-i", "1", "build/micaz/tos_image.xml"],
                     stdout=subprocess.PIPE, stderr=subprocess.PIPE)
img, err = p.communicate()
open("deluge.img", "wb").write(img)
ident = bytearray(img[:128]) + bytearray(128 - len(img[:128]))  # zeros if there is no image
pages = ident[8]
check(p.returncode == 0, "tos-build-deluge-image exits 0 (got %d; %s)" % (p.returncode, err.decode().strip()[-80:]))
check(len(img) > 384 and (len(img) - 384) % 1104 == 0 and pages == (len(img) - 384) // 1104,
      "image = ident + page CRCs + whole pages (%d bytes, %d pages)" % (len(img), pages))
check(crc16(list(ident[:10])) == (ident[10] << 8 | ident[11]), "ident CRC")
check(bytes(ident[12:28]).rstrip(b"\0") == b"BlinkAppC", "ident app name (got %r)" % bytes(ident[12:28]))

# 2. tos-deluge -p over TCP against the fake base station
port = "9101"
mote = subprocess.Popen([py, "/tests/fakemote.py", port, "deluge-frames.txt", "deluge.img"])
time.sleep(1)
p = subprocess.Popen([py, "/usr/local/bin/tos-deluge", "network@127.0.0.1:" + port, "-p", "1"],
                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
try:
    out = p.communicate(timeout=60)[0].decode()
except subprocess.TimeoutExpired:
    p.kill()
    out = p.communicate()[0].decode() + "\n(timeout)"
mote.kill()
mote.wait()
print("\n".join("  | " + l for l in out.strip().splitlines()[-12:]))
check(p.returncode == 0, "tos-deluge -p exits 0 (got %s)" % p.returncode)
for want in ["Prog Name:   FakeBase", "Node ID:     7", "Stored image 1", "Prog Name:   BlinkAppC",
             "Platform:    micaz", "Num Pages:   %d" % pages]:
    check(want in out, "tos-deluge -p prints %r" % want)

# 3. tos-dump.py over a serial port: a pty, opened by pySerial
master, slave = os.openpty()
dev = os.ttyname(slave)
p = subprocess.Popen([py, "-u", "/usr/local/bin/tos-dump.py", "serial@%s:57600" % dev],
                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
lines = []
threading.Thread(target=lambda: [lines.append(l.decode().rstrip("\n")) for l in iter(p.stdout.readline, b"")],
                 daemon=True).start()
msg = list(bytearray(b"hello from the mote\n"))
want = ["PRINTF: hello from the mote", "data: [1, 2, 3, 126, 125, 250]"]
t0 = time.time()
while time.time() - t0 < 15 and not all(any(w in l for l in lines) for w in want):
    time.sleep(0.5)  # tos.Serial first discards input for 1 s ("Flushing the serial port")
    os.write(master, bytes(am(100, msg + [0] * (28 - len(msg)))) + bytes(am(0x22, [1, 2, 3, 0x7e, 0x7d, 250])))
p.kill()
p.wait()
print("\n".join("  | " + l for l in lines[:6]))
check(any(l.startswith("Flushing the serial port") for l in lines), "tos-dump.py opens %s (pySerial)" % dev)
for w in want:
    check(any(w in l for l in lines), "tos-dump.py prints %r" % w)

print("PASS" if not fail else "FAIL")
sys.exit(1 if fail else 0)
