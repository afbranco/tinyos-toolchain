# Smoke test: BaseStation (micaz sim-sf). Boots 2 motes and checks that a TCP client gets the
# SerialForwarder handshake ("U" + protocol version) on port 9002.
import socket
import sys
import time
sys.path.insert(0, ".")
from TOSSIM import *

t = Tossim([])
sf = SerialForwarder(9002)
sf.process()
for i in (1, 2):
    m = t.getNode(i)
    for _ in range(100):
        m.addNoiseTraceReading(-98)
    m.createNoiseModel()
    m.bootAtTime(1000 * i)

c = socket.create_connection(("127.0.0.1", 9002), timeout=5)
c.sendall(b"U ")
got = b""
t0 = time.time()
while len(got) < 2 and time.time() - t0 < 5:
    sf.process()
    t.runNextEvent()
    try:
        c.settimeout(0.05)
        got += c.recv(2 - len(got))
    except socket.timeout:
        pass

print("handshake=%r" % got)
ok = got == b"U "
print("PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
