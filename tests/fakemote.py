# A fake mote for the Python SDK's tos module (tos.py), for deluge_check.py. Python 2 and 3.
# Speaks the TinyOS serial protocol (TEP 113: HDLC framing, CRC, acks) and answers as a
# Deluge T2 base station: FlashManager (AM 0x53) and DelugeManager (AM 0x54) commands on a
# simulated flash.
#   python fakemote.py <TCP port> <frame log> <initial image 1>
# serves one tos-deluge connection (the network@ source, as a MIB600) and logs each frame
# it receives. frame() and am() also build frames for a serial (pty) test.
import socket, sys


def crc16(data):
    crc = 0
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) if crc & 0x8000 else (crc << 1)
            crc &= 0xffff
    return crc


def frame(body):
    """HDLC frame (flags, escapes, CRC) around a serial packet body."""
    c = crc16(body)
    out = [0x7e]
    for b in body + [c & 0xff, c >> 8]:
        out += [0x7d, b ^ 0x20] if b in (0x7e, 0x7d) else [b]
    return bytearray(out + [0x7e])


def am(amtype, payload):
    """Active message in a no-ack data frame (dispatch 0) from node 1."""
    return frame([69, 0, 0xff, 0xff, 0, 1, len(payload), 0, amtype] + payload)


def be(v):
    r = 0
    for x in v:
        r = (r << 8) | x
    return r


def unframe(conn):
    """Yield the unescaped body of each frame read from a socket."""
    buf = []
    while True:
        data = conn.recv(4096)
        if not data:
            return
        for b in bytearray(data):
            if b != 0x7e:
                buf.append(b)
            elif buf:
                body, esc = [], False
                for x in buf:
                    if esc:
                        body.append(x ^ 0x20)
                        esc = False
                    elif x == 0x7d:
                        esc = True
                    else:
                        body.append(x)
                del buf[:]
                yield body


def base_station(conn, flash, log):
    for body in unframe(conn):
        ok = crc16(body[:-2]) == (body[-2] | (body[-1] << 8))
        proto, seqno, amtype, payload = body[0], body[1], body[9], body[10:-2]
        log.write("crc=%s proto=%d seq=%d type=%02x | %s\n" % (
            ok, proto, seqno, amtype, " ".join("%02x" % x for x in payload)))
        log.flush()
        if proto == 68:  # the sender wants an ack
            conn.sendall(frame([67, seqno]))
        err, data = 0, []
        if amtype == 0x53:
            cmd, img, off, length, wdata = payload[0], payload[1], be(payload[2:6]), be(payload[6:8]), payload[8:]
            f = flash.setdefault(img, [])
            if cmd == 0:  # erase
                del f[:]
            elif cmd == 1:  # write
                f += [0xff] * max(0, off + length - len(f))
                f[off:off + length] = wdata[:length]
            elif cmd == 2:  # read
                chunk = f[off:off + length]
                data = chunk + [0xff] * (length - len(chunk))
            elif cmd == 6:  # ident of the running program: ShortIdent
                name = list(bytearray(b'FakeBase'))
                data = name + [0] * (16 - len(name)) + [0x5f, 0x5e, 0x10, 0x00] + [0xde, 0xad, 0xbe, 0xef] + [0, 7]
        conn.sendall(am(amtype, [err] + data))


if __name__ == "__main__":
    port, logpath, imgpath = int(sys.argv[1]), sys.argv[2], sys.argv[3]
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(('127.0.0.1', port))
    srv.listen(1)
    conn, _ = srv.accept()
    base_station(conn, {1: list(bytearray(open(imgpath, 'rb').read()))}, open(logpath, 'w'))
