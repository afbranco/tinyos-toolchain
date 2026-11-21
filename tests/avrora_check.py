# Checks Avrora's output for the AVR firmware built by smoke.sh (micaz, 7.3728 MHz):
#   python3 avrora_check.py blink <avrora output>
#   python3 avrora_check.py radio <avrora output> <min packets per node>
# blink: Blink toggles its three LEDs every 250, 500 and 1000 TinyOS milliseconds (1/1024 s),
#   i.e. every 1800000, 3600000 and 7200000 cycles. Each LED's toggles must be that far apart.
# radio: RadioCountToLeds on 2 nodes; each node must receive at least <min> packets and none
#   may be corrupted (Avrora's packet monitor table).
import re
import sys

mode, path = sys.argv[1], sys.argv[2]
lines = open(path).read().splitlines()
fail = []

if mode == "blink":
    # Avrora prints the 3 LEDs as columns, LED0 (Blink's 250 ms timer) being the rightmost one
    # (seen in the output), so the expected periods go right to left.
    states = []
    for l in lines:
        m = re.match(r"\s*0\s+(\d+)\s+(on|off)\s+(on|off)\s+(on|off)\s*$", l)
        if m:
            states.append((int(m.group(1)), m.group(2, 3, 4)))
    # Skip the boot pattern (all LEDs stepped within a few cycles): keep events from the first
    # moment all LEDs are off after the boot sequence.
    boot_end = next(i for i in range(1, len(states)) if states[i][1] == ("off",) * 3
                    and states[i][0] - states[0][0] < 100)
    states = states[boot_end:]
    for col, period in ((2, 1800000), (1, 3600000), (0, 7200000)):
        changes = [t for (t, s), (_, prev) in zip(states[1:], states) if s[col] != prev[col]]
        gaps = sorted(set(b - a for a, b in zip(changes, changes[1:])))
        print("LED column %d: %d toggles, gaps %s (expected %d)" % (col, len(changes), gaps, period))
        if len(changes) < 2 or gaps != [period]:
            fail.append("LED column %d should toggle every %d cycles" % (col, period))

elif mode == "radio":
    need = int(sys.argv[3])
    rows = [l.split() for l in lines if re.match(r"\s*\d+\s+\d+ / \d+\s+\d+ / \d+\s+\d+\s+\d+\s*$", l)]
    for r in rows:
        node, recv_p, corrupted = r[0], int(r[6]), int(r[7])
        print("node %s: received %d packets, %d corrupted bytes" % (node, recv_p, corrupted))
        if recv_p < need:
            fail.append("node %s should receive at least %d packets" % (node, need))
        if corrupted:
            fail.append("node %s got corrupted bytes" % node)
    if len(rows) != 2:
        fail.append("expected the packet table for 2 nodes, got %d rows" % len(rows))

for f in fail:
    print("FAIL: " + f)
print("PASS" if not fail else "FAIL")
sys.exit(1 if fail else 0)
