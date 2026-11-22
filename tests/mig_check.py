# mig check, run by smoke.sh in RadioCountToLeds after "make micaz sim" with its mig targets
# (RadioCountMsg.py and RadioCountMsg.class):
#   python mig_check.py <noise trace>
# 1. The Python class: set_counter(0x1234) gives the bytes 12 34 (nx_uint16_t is big-endian),
#    as bytes in Python 3; offset/size methods give integers.
# 2. The Java class gives the same bytes.
# 3. TOSSIM: messages built by the Python class are delivered to a mote (Packet.setData); the
#    mote shows the counter's low 3 bits on its LEDs (counter 5: on off on; 2: off on off).
import os
import subprocess
import sys

sys.path.insert(0, ".")
sys.path.insert(0, os.path.join(os.environ["TOSROOT"], "support/sdk/python"))
from RadioCountMsg import RadioCountMsg
from TOSSIM import Tossim

fail = []


def check(ok, what):
    print("  %s: %s" % ("ok" if ok else "FAIL", what))
    if not ok:
        fail.append(what)


m = RadioCountMsg()
m.set_counter(0x1234)
data = m.dataGet()
check(bytearray(data) == bytearray([0x12, 0x34]), "Python: set_counter(0x1234) -> bytes 12 34")
if sys.version_info[0] >= 3:
    check(isinstance(data, bytes), "Python 3: dataGet() is bytes")
check(m.get_counter() == 0x1234, "Python: get_counter() reads it back")
sizes = (m.offset_counter(), m.size_counter())
check(sizes == (0, 2) and all(isinstance(v, int) for v in sizes),
      "Python: offset_counter(), size_counter() == 0, 2 as int (got %r)" % (sizes,))

with open("MigJ.java", "w") as f:
    f.write("public class MigJ { public static void main(String[] a) {\n"
            "  RadioCountMsg m = new RadioCountMsg(); m.set_counter(0x1234);\n"
            "  StringBuilder s = new StringBuilder();\n"
            "  for (byte b : m.dataGet()) s.append(String.format(\"%02x\", b));\n"
            "  System.out.println(m.amType() + \" \" + s); } }\n")
try:
    subprocess.check_call(["javac", "MigJ.java"])
    java = subprocess.check_output(["java", "MigJ"]).decode().split()
except (OSError, subprocess.CalledProcessError) as e:
    java = ["error: %s" % e]
check(java == [str(m.get_amType()), "1234"],
      "Java: same AM type (%d) and bytes 1234 (got %s)" % (m.get_amType(), " ".join(java)))

t = Tossim([])
log = open("mig_dbg.txt", "w")
for ch in ("RadioCountToLedsC", "LedsC"):
    t.addChannel(ch, log)
node = t.getNode(1)
for l in open(sys.argv[1]).readlines()[:1000]:
    if l.strip():
        node.addNoiseTraceReading(int(l))
node.createNoiseModel()
node.bootAtTime(1000)
sent = (5, 2)
for i, counter in enumerate(sent):
    msg = RadioCountMsg()
    msg.set_counter(counter)
    pkt = t.newPacket()
    pkt.setData(msg.dataGet())
    pkt.setType(msg.get_amType())
    pkt.setDestination(1)
    pkt.deliver(1, (i + 1) * t.ticksPerSecond())
while t.time() < (len(sent) + 1) * t.ticksPerSecond():
    if not t.runNextEvent():
        break
log.close()

# The LED lines that follow each "Received packet of length 2".
seen, cur = [], None
for l in open("mig_dbg.txt"):
    if "Received packet of length 2" in l:
        cur = {}
        seen.append(cur)
    elif "LEDS: Led" in l and cur is not None:
        w = l.split("LEDS: Led")[1].split()
        cur[int(w[0])] = w[1].rstrip(".")
for counter, leds in zip(sent, seen):
    want = dict((n, "on" if counter & (1 << n) else "off") for n in range(3))
    check(leds == want, "TOSSIM: counter %d delivered, LEDs %s (got %s)" % (counter, want, leds))
check(len(seen) == len(sent), "TOSSIM: %d messages received (got %d)" % (len(sent), len(seen)))

print("PASS" if not fail else "FAIL")
sys.exit(1 if fail else 0)
