"""Round-trip: parse each retail file, rebuild it, require byte-identical output."""
import os, sys
from axmail import BbsFile, MailFile, verify, BBS_HASH, MAIL_HASH

D = os.path.expanduser("~/Downloads")
fail = 0
for name, cls, off in (("forest_bbs_USA.bin", BbsFile, BBS_HASH),
                       ("forest_mail_USA.bin", MailFile, MAIL_HASH)):
    orig = open(os.path.join(D, name), "rb").read()
    assert verify(orig, off), "%s: retail file failed verification" % name
    rebuilt = cls.parse(orig).build()
    ok = rebuilt == orig
    fail += not ok
    print("%-22s parse+build byte-identical: %s" % (name, "YES" if ok else "NO"))
    if not ok:
        for i, (a, b) in enumerate(zip(orig, rebuilt)):
            if a != b:
                print("   first diff at %#x: orig %02x rebuilt %02x" % (i, a, b))
                break
sys.exit(fail)
