# API check (run in a built RadioCountToLeds dir, micaz sim): the parts of the TOSSIM Python
# binding that the smoke runs do not touch, and that changed with the Python 3 port.
import sys
sys.path.insert(0, ".")
from TOSSIM import *

PY3 = sys.version_info[0] >= 3
fail = []

# nesc_app_t (in) and variable_string_t (out) typemaps.
t = Tossim(["RadioCountToLedsC.counter", "scalar", "uint16_t"])

# FILE* typemap: TOSSIM drops duplicate outputs by file descriptor, so one Python file added
# twice to a channel must still get each line once (Python 3 must not dup() the descriptor
# on every call). "once" is the control. (removeChannel is not checked: it never worked in
# TinyOS 2.1.2, see README.)
twice_path, once_path = "/tmp/api_check_twice.txt", "/tmp/api_check_once.txt"
twice_f, once_f = open(twice_path, "w"), open(once_path, "w")
t.addChannel("RadioCountToLedsC", twice_f)
t.addChannel("RadioCountToLedsC", twice_f)
t.addChannel("RadioCountToLedsC", once_f)

m = t.getNode(1)
for _ in range(100):
    m.addNoiseTraceReading(-98)
m.createNoiseModel()
m.bootAtTime(1000)
for _ in range(2000):
    t.runNextEvent()
v = m.getVariable("RadioCountToLedsC.counter").getData()
print("getVariable: %r" % (v,))
if type(v) is not int or v <= 0:
    fail.append("getVariable should give a positive int")

# (char *data, int len) in, char* data() out: payloads are binary. No zero byte, so that
# Python 2 (C string semantics, kept as is) can be checked too.
raw = bytes(bytearray([65, 1, 0x7f, 0x80, 0xff, 66]))
p = t.newPacket()
p.setData(raw)
p.setLength(len(raw))
d = p.data()
print("data: %r" % (d,))
if d[:len(raw)] != raw:
    fail.append("data() should give back the bytes given to setData()")
if PY3 and type(d) is not bytes:
    fail.append("data() should be bytes in Python 3")

# Flush, not close: TOSSIM keeps writing to these FILE*s until the process ends.
twice_f.flush()
once_f.flush()
n_twice = len(open(twice_path).readlines())
n_once = len(open(once_path).readlines())
print("channel lines: twice=%d once=%d" % (n_twice, n_once))
if n_once == 0:
    fail.append("the RadioCountToLedsC channel should produce output")
if n_twice != n_once:
    fail.append("a file added twice to a channel should get each line once")

for f in fail:
    print("FAIL: " + f)
print("PASS" if not fail else "FAIL")
sys.exit(1 if fail else 0)
