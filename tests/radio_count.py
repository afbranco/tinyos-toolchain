# Smoke test: RadioCountToLeds (micaz sim), 2 motes for 20 simulated seconds.
# Passes if simulated time reaches 20 s and mote 2 receives packets from mote 1.
import sys
sys.path.insert(0, ".")
from TOSSIM import *

SIM_S = 20
t = Tossim([])
r = t.radio()
out = open("/tmp/radio_count_dbg.txt", "w")
for ch in ("RadioCountToLedsC", "TossimPacketModelC"):
    t.addChannel(ch, out)
for a, b in ((1, 2), (2, 1)):
    r.add(a, b, -50.0)
noise = [l.strip() for l in open(sys.argv[1]).readlines()[:1000] if l.strip()]
for i in (1, 2):
    m = t.getNode(i)
    for l in noise:
        m.addNoiseTraceReading(int(l))
    m.createNoiseModel()
    m.bootAtTime(1000 * i)

events = 0
while t.time() < SIM_S * t.ticksPerSecond():
    # runNextEvent() returns False when the queue is empty: that is not an event, and
    # counting it would make an idle network look like a hang.
    if not t.runNextEvent():
        break
    events += 1
out.close()

sim_s = t.time() / float(t.ticksPerSecond())
received = sum(1 for l in open("/tmp/radio_count_dbg.txt") if "Received packet" in l)
print("events=%d sim_s=%.2f received=%d" % (events, sim_s, received))
ok = sim_s >= SIM_S and received > 0
print("PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
