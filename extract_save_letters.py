#!/usr/bin/env python3
"""Pull letters out of Animal Crossing: Wild World save files.

In a save, letters are stored back-to-back at exactly 0xF4 stride -- the same
0xF4-byte structure that forest_mail_*.bin wraps with a serial and an HMAC.
This finds them by locating the encoded greeting "Dear" and backing up to the
start of the containing struct (greeting lives at +0x34).

Works on raw 256KB saves and on Action Replay .duc/.dst dumps (the 500-byte AR
header just shifts everything; the scan is offset-independent).

    python3 extract_save_letters.py SAVE [SAVE ...]           # list letters
    python3 extract_save_letters.py --fields SAVE [SAVE ...]  # tabulate unk_*

This is the tool that identified recipient_town / recipient_player /
sender_town / sender_player.  The direction comes from the closing text: where
both player names are non-blank, the "From X" sign-off names the 0x1C/0x26 pair
and never the 0x04/0x0E pair.  Note a save also stores letters the player wrote,
so neither pair is constant across a whole save.
"""

from __future__ import annotations

import argparse
import collections
import os

from axmail import MailFile, NO_ITEM, encode_text

LETTER_LEN = 0xF4
GREETING_OFF = 0x34


def find_letters(data: bytes) -> list[bytes]:
    """Return the unique 0xF4-byte letter structs found in *data*."""
    needle = encode_text("Dear")
    seen: dict[bytes, int] = {}
    i = data.find(needle)
    while i != -1:
        base = i - GREETING_OFF
        if base >= 0 and base + LETTER_LEN <= len(data):
            seen.setdefault(data[base:base + LETTER_LEN], base)
        i = data.find(needle, i + 1)
    return list(seen)


def as_mail(letter: bytes) -> MailFile:
    """Parse a bare 0xF4 letter by padding it out to a full mail file."""
    return MailFile.parse(letter + bytes(0x108 - LETTER_LEN), check=False)


def is_wellformed(m: MailFile) -> bool:
    """Reject false positives.

    Scanning for "Dear" also hits the word inside a letter *body*, which yields a
    struct start 0x34 bytes earlier that is really mid-letter garbage, plus
    erased mailbox slots that are solid 0xFF.  Requiring unk_00 == 0 (true for
    every genuine letter sampled) and sane names removes both.
    """
    if m.unk_00 != 0:
        return False
    if not (m.greeting.startswith("Dear") and m.body and m.closing):
        return False
    for ref in (m.recipient_town, m.recipient_player,
                m.sender_town, m.sender_player):
        if "\\x" in ref.name:          # unmapped bytes -> not a real name
            return False
    return True


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("saves", nargs="+")
    p.add_argument("--fields", action="store_true",
                   help="tabulate the unidentified fields instead of listing text")
    p.add_argument("--all", action="store_true",
                   help="include malformed hits (false positives from body text)")
    args = p.parse_args(argv)

    found = []
    for path in args.saves:
        data = open(path, "rb").read()
        for letter in find_letters(data):
            m = as_mail(letter)
            if args.all or is_wellformed(m):
                found.append((os.path.basename(path), m))

    if not found:
        print("no letters found")
        return 1

    if args.fields:
        print("%d letters from %d save(s)\n" % (found and len(found), len(args.saves)))
        # unk_00 is omitted: is_wellformed() filters on it, so counting it here
        # would be circular.
        for name in ("unk_18", "unk_1a", "unk_30", "unk_32", "unk_f2"):
            c = collections.Counter(getattr(m, name) for _, m in found)
            print("%-8s %s" % (name, c.most_common(6)))
        c = collections.Counter(m.unk_ec.hex() for _, m in found)
        print("%-8s %s" % ("unk_ec", c.most_common(5)))
        c = collections.Counter(m.attached_item for _, m in found)
        print("%-8s %s" % ("item", [("0x%04X" % v, n) for v, n in c.most_common(6)]))
        # Direction test: a sign-off reads "From <sender>", so whichever pair the
        # closing text names is the sender.  This is the evidence that fixes
        # 0x1C/0x26 as sender and 0x04/0x0E as recipient.
        sender = recipient = ambiguous = 0
        for _, m in found:
            sp = m.sender_player.name.strip()
            rp = m.recipient_player.name.strip()
            if not sp or not rp:
                continue
            in_s, in_r = sp in m.closing, rp in m.closing
            if in_s and not in_r:
                sender += 1
            elif in_r and not in_s:
                recipient += 1
            else:
                ambiguous += 1
        print("\ndirection test (letters with both player names non-blank):")
        print("  closing names the 0x1C/0x26 pair only : %d" % sender)
        print("  closing names the 0x04/0x0E pair only : %d" % recipient)
        print("  ambiguous (both or neither)           : %d" % ambiguous)
        return 0

    for name, m in found:
        item = "" if m.attached_item == NO_ITEM else "  item=0x%04X" % m.attached_item
        print("--- %s%s" % (name, item))
        print("    to   %-9s of %s" % (m.recipient_player.name or "(blank)",
                                       m.recipient_town.name or "(blank)"))
        print("    from %-9s of %s" % (m.sender_player.name or "(blank)",
                                       m.sender_town.name or "(blank)"))
        print("    %s" % m.greeting)
        for line in m.body.split("\n"):
            print("      %s" % line)
        print("    %s" % m.closing)
    print("\n%d letters" % len(found))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
