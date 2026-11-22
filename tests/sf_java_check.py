# Java over the SerialForwarder, run by smoke.sh in BaseStation (micaz sim-sf):
#   python sf_java_check.py
# The path Terra's TerraControl uses: radio -> BaseStation mote -> serial -> TOSSIM's
# SerialForwarder (TCP 9002) -> TinyOS's Java SDK (MoteIF, here MsgReader with -comm sf@)
# -> a mig-generated Java class. RadioCountMsg packets (counter 0x1234) are delivered over the
# radio to the BaseStation mote, and MsgReader must print them decoded.
import os
import subprocess
import sys
import time

sys.path.insert(0, ".")
from TOSSIM import SerialForwarder, Tossim

hdr = os.path.join(os.environ["TOSROOT"], "apps/RadioCountToLeds/RadioCountToLeds.h")
subprocess.check_call(["mig", "java", "-target=micaz", "-java-classname=RadioCountMsg", hdr,
                       "radio_count_msg", "-o", "RadioCountMsg.java"])
subprocess.check_call(["javac", "RadioCountMsg.java"])

t = Tossim([])
sf = SerialForwarder(9002)
node = t.getNode(1)
for _ in range(100):
    node.addNoiseTraceReading(-98)
node.createNoiseModel()
node.bootAtTime(1000)
# Boot the mote. BaseStation has no timers: once booted its event queue empties and time
# stops, so stop then too.
while t.time() < t.ticksPerSecond() // 2 and t.runNextEvent():
    pass

log = open("msgreader.txt", "w")
reader = subprocess.Popen(["java", "net.tinyos.tools.MsgReader", "-comm", "sf@localhost:9002",
                           "RadioCountMsg"], stdout=log, stderr=subprocess.STDOUT)
t0 = time.time()
while time.time() - t0 < 6:  # let MsgReader connect and do the handshake
    sf.process()
    time.sleep(0.01)

sent = 3
for i in range(sent):
    pkt = t.newPacket()
    pkt.setData(b"\x12\x34")
    pkt.setType(6)  # RadioCountMsg's AM type
    pkt.setDestination(0xFFFF)
    pkt.deliver(1, t.time() + (i + 1) * t.ticksPerSecond() // 10)
t0 = time.time()
while time.time() - t0 < 6:
    sf.process()
    t.runNextEvent()
    time.sleep(0.001)
reader.kill()
reader.wait()
log.close()

out = open("msgreader.txt").read()
print("\n".join("  | " + l for l in out.strip().splitlines()[-6:]))
got = out.count("counter=0x1234")
print("MsgReader decoded %d of %d messages" % (got, sent))
ok = got == sent
print("PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
