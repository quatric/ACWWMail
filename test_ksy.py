"""Walk the .ksy seq (fixed-size fields only) and check it tiles each file exactly."""
import os, sys, yaml

SZ = {"u1": 1, "u2": 2, "u4": 4}

def walk(spec, types, off=0):
    out = []
    for f in spec:
        if "size" in f:
            n = f["size"]
        elif f["type"] in SZ:
            n = SZ[f["type"]]
        else:
            sub = types[f["type"]]["seq"]
            n = sum(walk(sub, types))
        out.append(n)
    return out

fail = 0
for ksy, name, want in (("acww_forest_bbs.ksy", "forest_bbs_USA.bin", 0xD2),
                        ("acww_forest_mail.ksy", "forest_mail_USA.bin", 0x108)):
    d = yaml.safe_load(open(ksy))
    sizes = walk(d["seq"], d.get("types", {}))
    total = sum(sizes)
    real = len(open(os.path.expanduser("~/Downloads/" + name), "rb").read())
    ok = total == want == real
    fail += not ok
    print("%-22s schema total %#x, declared %#x, actual file %#x -> %s"
          % (ksy, total, want, real, "OK" if ok else "MISMATCH"))
    off = 0
    for f, n in zip(d["seq"], sizes):
        print("    %04x  %-10s %s" % (off, f["id"], f.get("type", "bytes[%#x]" % n)))
        off += n
sys.exit(fail)
