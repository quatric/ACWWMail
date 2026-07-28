#!/usr/bin/env python3
"""Read, write and sign Animal Crossing: Wild World "axmail" WFC download files.

These are the files the game fetched from

    http://axing.nintendowifi.net/axmail/forest_bbs_USA.bin
    http://axing.nintendowifi.net/axmail/forest_mail_USA.bin

(plus a ``?brid=ADME30io38k`` style parameter identifying the title).

Both files are authenticated with HMAC-MD5 using a key baked into the ARM9:

    hash = HMAC-MD5(key=b"HNANKTMSYNKASSNK",
                    msg=<entire file, with the 16 hash bytes zeroed>)

The message is the *whole* fixed-size file (0xD2 for BBS, 0x108 for mail), not a
prefix, and the hash field must be zeroed before hashing.  See README.md for the
matching ROM addresses.

EXPERIMENTAL: the outer framing (sizes, serial, hash) is verified byte-exact
against retail files and against the game's own verifier.  The mail letter
header was mapped against 213 letters extracted from 18 GameFAQs save files;
fields still named ``unk_*`` are characterised by observed value distributions
but not identified, so treat those names as placeholders.
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import sys
from dataclasses import dataclass, field

from ww_charset import CHARS, ENCODE

# ---------------------------------------------------------------------------
# constants
# ---------------------------------------------------------------------------

#: 16-byte HMAC key, stored as plain ASCII at ARM9 0x02000b6c.
HMAC_KEY = b"HNANKTMSYNKASSNK"

BBS_SIZE = 0xD2
BBS_TEXT = 0x00
BBS_TEXT_LEN = 0xC0
BBS_SERIAL = 0xC0
BBS_HASH = 0xC2

MAIL_SIZE = 0x108
MAIL_SERIAL = 0xF4
MAIL_HASH = 0xF6

HASH_LEN = 0x10

#: Wild World's "empty item" sentinel, used by `MailFile.attached_item`.
NO_ITEM = 0xFFF1


class BadHash(ValueError):
    """Raised when a file's stored HMAC does not match its contents."""


# ---------------------------------------------------------------------------
# text codec
# ---------------------------------------------------------------------------


def decode_text(raw: bytes, stop_at_nul: bool = True) -> str:
    """Decode Wild World character bytes to a Python string.

    NUL (0x00) is the pad/terminator.  Unmapped slots come back as ``\\xNN``.
    """
    out = []
    for b in raw:
        if b == 0x00:
            if stop_at_nul:
                break
            continue
        ch = CHARS[b]
        out.append(ch if ch else "\\x%02x" % b)
    return "".join(out)


def encode_text(text: str, size: int | None = None) -> bytes:
    """Encode a Python string to Wild World character bytes.

    If *size* is given the result is NUL-padded (or an error is raised when the
    text does not fit).
    """
    out = bytearray()
    for ch in text:
        if ch == "\r":
            continue
        try:
            out.append(ENCODE[ch])
        except KeyError:
            raise ValueError(
                "character %r has no Wild World encoding" % ch
            ) from None
    if size is not None:
        if len(out) > size:
            raise ValueError(
                "encoded text is %d bytes, field holds %d" % (len(out), size)
            )
        out.extend(b"\0" * (size - len(out)))
    return bytes(out)


# ---------------------------------------------------------------------------
# hashing
# ---------------------------------------------------------------------------


def compute_hash(buf: bytes, hash_off: int) -> bytes:
    """HMAC-MD5 over *buf* with the 16 bytes at *hash_off* zeroed."""
    d = bytearray(buf)
    d[hash_off:hash_off + HASH_LEN] = b"\0" * HASH_LEN
    return hmac.new(HMAC_KEY, bytes(d), hashlib.md5).digest()


def sign(buf: bytes, hash_off: int) -> bytes:
    """Return *buf* with a freshly computed hash written in at *hash_off*."""
    d = bytearray(buf)
    d[hash_off:hash_off + HASH_LEN] = compute_hash(bytes(d), hash_off)
    return bytes(d)


def verify(buf: bytes, hash_off: int) -> bool:
    stored = buf[hash_off:hash_off + HASH_LEN]
    return hmac.compare_digest(stored, compute_hash(buf, hash_off))


# ---------------------------------------------------------------------------
# forest_bbs_*.bin
# ---------------------------------------------------------------------------


@dataclass
class BbsFile:
    """The town bulletin-board message.

    Layout (0xD2 bytes)::

        0x00  char text[0xC0]   message, NUL-padded, 0x86 = newline
        0xC0  u16  serial       dedup id; ignored if it equals the stored one
        0xC2  u8   hash[0x10]   HMAC-MD5
    """

    text: str = ""
    serial: int = 0

    @classmethod
    def parse(cls, buf: bytes, check: bool = True) -> "BbsFile":
        if len(buf) != BBS_SIZE:
            raise ValueError("expected %#x bytes, got %#x" % (BBS_SIZE, len(buf)))
        if check and not verify(buf, BBS_HASH):
            raise BadHash("forest_bbs hash mismatch")
        return cls(
            text=decode_text(buf[BBS_TEXT:BBS_TEXT + BBS_TEXT_LEN]),
            serial=int.from_bytes(buf[BBS_SERIAL:BBS_SERIAL + 2], "little"),
        )

    def build(self) -> bytes:
        buf = bytearray(BBS_SIZE)
        buf[BBS_TEXT:BBS_TEXT + BBS_TEXT_LEN] = encode_text(self.text, BBS_TEXT_LEN)
        buf[BBS_SERIAL:BBS_SERIAL + 2] = self.serial.to_bytes(2, "little")
        return sign(bytes(buf), BBS_HASH)


# ---------------------------------------------------------------------------
# forest_mail_*.bin
# ---------------------------------------------------------------------------


@dataclass
class NameRef:
    """A (u16 id, char name[8]) pair -- the game's usual player/town reference."""

    id: int = 0
    name: str = ""

    @classmethod
    def parse(cls, buf: bytes, off: int) -> "NameRef":
        return cls(
            id=int.from_bytes(buf[off:off + 2], "little"),
            name=decode_text(buf[off + 2:off + 10]),
        )

    def pack(self) -> bytes:
        return self.id.to_bytes(2, "little") + encode_text(self.name, 8)


@dataclass
class MailFile:
    """A letter pushed from the WFC server.

    The first 0xF4 bytes are the game's ordinary letter structure -- in a save
    file, letters sit back-to-back at exactly 0xF4 stride.  Layout (0x108)::

        0x00  u32      unk_00            (0)
        0x04  NameRef  recipient_town    id 0xC1BD, "Redmond"
        0x0E  NameRef  recipient_player  id 0x5C04, name blank
        0x18  u16      unk_18            (0)
        0x1A  u16      unk_1a            (3; delivered letters show 2)
        0x1C  NameRef  sender_town       id 0xC1BD, "Redmond"
        0x26  NameRef  sender_player     id 0x81D4, "Nintendo"
        0x30  u16      unk_30            (1; delivered letters show 0)
        0x32  u16      unk_32            (2)
        0x34  char     greeting[0x18]    "Dear ,"
        0x4C  char     body[0x80]
        0xCC  char     closing[0x20]     "From Nintendo"
        0xEC  u8       unk_ec[4]         05 35 42 11
        0xF0  u16      attached_item     0x13DF (0xFFF1 = none)
        0xF2  u16      unk_f2            (0)
        0xF4  u16      serial            dedup id
        0xF6  u8       hash[0x10]        HMAC-MD5
        0x106 u16      pad               (0)

    Sender/recipient direction was established from 213 letters extracted from
    18 GameFAQs saves: where both player names are non-blank, the "From X"
    closing names the 0x1C/0x26 pair in 10 of 12 cases and the 0x04/0x0E pair in
    none.  See extract_save_letters.py.
    """

    unk_00: int = 0
    recipient_town: NameRef = field(default_factory=NameRef)
    recipient_player: NameRef = field(default_factory=NameRef)
    unk_18: int = 0
    unk_1a: int = 3
    sender_town: NameRef = field(default_factory=NameRef)
    sender_player: NameRef = field(default_factory=NameRef)
    unk_30: int = 1
    unk_32: int = 2
    greeting: str = ""
    body: str = ""
    closing: str = ""
    unk_ec: bytes = bytes(4)
    attached_item: int = NO_ITEM
    unk_f2: int = 0
    serial: int = 0
    pad: int = 0

    @classmethod
    def parse(cls, buf: bytes, check: bool = True) -> "MailFile":
        if len(buf) != MAIL_SIZE:
            raise ValueError("expected %#x bytes, got %#x" % (MAIL_SIZE, len(buf)))
        if check and not verify(buf, MAIL_HASH):
            raise BadHash("forest_mail hash mismatch")
        u16 = lambda o: int.from_bytes(buf[o:o + 2], "little")
        return cls(
            unk_00=int.from_bytes(buf[0x00:0x04], "little"),
            recipient_town=NameRef.parse(buf, 0x04),
            recipient_player=NameRef.parse(buf, 0x0E),
            unk_18=u16(0x18),
            unk_1a=u16(0x1A),
            sender_town=NameRef.parse(buf, 0x1C),
            sender_player=NameRef.parse(buf, 0x26),
            unk_30=u16(0x30),
            unk_32=u16(0x32),
            greeting=decode_text(buf[0x34:0x4C]),
            body=decode_text(buf[0x4C:0xCC]),
            closing=decode_text(buf[0xCC:0xEC]),
            unk_ec=bytes(buf[0xEC:0xF0]),
            attached_item=u16(0xF0),
            unk_f2=u16(0xF2),
            serial=u16(MAIL_SERIAL),
            pad=u16(0x106),
        )

    def build(self) -> bytes:
        buf = bytearray(MAIL_SIZE)
        buf[0x00:0x04] = self.unk_00.to_bytes(4, "little")
        buf[0x04:0x0E] = self.recipient_town.pack()
        buf[0x0E:0x18] = self.recipient_player.pack()
        buf[0x18:0x1A] = self.unk_18.to_bytes(2, "little")
        buf[0x1A:0x1C] = self.unk_1a.to_bytes(2, "little")
        buf[0x1C:0x26] = self.sender_town.pack()
        buf[0x26:0x30] = self.sender_player.pack()
        buf[0x30:0x32] = self.unk_30.to_bytes(2, "little")
        buf[0x32:0x34] = self.unk_32.to_bytes(2, "little")
        buf[0x34:0x4C] = encode_text(self.greeting, 0x18)
        buf[0x4C:0xCC] = encode_text(self.body, 0x80)
        buf[0xCC:0xEC] = encode_text(self.closing, 0x20)
        if len(self.unk_ec) != 4:
            raise ValueError("unk_ec must be 4 bytes")
        buf[0xEC:0xF0] = self.unk_ec
        buf[0xF0:0xF2] = self.attached_item.to_bytes(2, "little")
        buf[0xF2:0xF4] = self.unk_f2.to_bytes(2, "little")
        buf[MAIL_SERIAL:MAIL_SERIAL + 2] = self.serial.to_bytes(2, "little")
        buf[0x106:0x108] = self.pad.to_bytes(2, "little")
        return sign(bytes(buf), MAIL_HASH)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _kind(buf: bytes) -> str:
    if len(buf) == BBS_SIZE:
        return "bbs"
    if len(buf) == MAIL_SIZE:
        return "mail"
    raise SystemExit("unrecognised size %#x (want %#x or %#x)"
                     % (len(buf), BBS_SIZE, MAIL_SIZE))


def cmd_show(args) -> int:
    buf = open(args.file, "rb").read()
    kind = _kind(buf)
    off = BBS_HASH if kind == "bbs" else MAIL_HASH
    ok = verify(buf, off)
    print("file    : %s (%s, %#x bytes)" % (args.file, kind, len(buf)))
    print("hash    : %s  %s" % (buf[off:off + HASH_LEN].hex(),
                                "OK" if ok else "MISMATCH"))
    if not ok:
        print("expected: %s" % compute_hash(buf, off).hex())
    if kind == "bbs":
        m = BbsFile.parse(buf, check=False)
        print("serial  : %d (0x%04x)" % (m.serial, m.serial))
        print("--- text ---")
        print(m.text)
    else:
        m = MailFile.parse(buf, check=False)
        print("serial  : %d (0x%04x)" % (m.serial, m.serial))
        for n in ("recipient_town", "recipient_player",
                  "sender_town", "sender_player"):
            r = getattr(m, n)
            print("%-16s: id=0x%04x name=%r" % (n, r.id, r.name))
        print("attached_item   : 0x%04X%s"
              % (m.attached_item, " (none)" if m.attached_item == NO_ITEM else ""))
        print("unk_ec          : %s" % m.unk_ec.hex())
        print("--- greeting ---\n%s" % m.greeting)
        print("--- body ---\n%s" % m.body)
        print("--- closing ---\n%s" % m.closing)
    return 0 if ok else 1


def cmd_sign(args) -> int:
    buf = open(args.file, "rb").read()
    off = BBS_HASH if _kind(buf) == "bbs" else MAIL_HASH
    out = sign(buf, off)
    open(args.out or args.file, "wb").write(out)
    print("wrote %s (hash %s)" % (args.out or args.file,
                                  out[off:off + HASH_LEN].hex()))
    return 0


def cmd_bbs(args) -> int:
    text = open(args.text, encoding="utf-8").read() if args.text else sys.stdin.read()
    buf = BbsFile(text=text.rstrip("\n"), serial=args.serial).build()
    open(args.out, "wb").write(buf)
    print("wrote %s (%#x bytes, serial %d, hash %s)"
          % (args.out, len(buf), args.serial, buf[BBS_HASH:BBS_HASH + HASH_LEN].hex()))
    return 0


def cmd_mail(args) -> int:
    """Build a letter by editing an existing one -- safest while the header
    fields are still partly unknown."""
    base = MailFile.parse(open(args.template, "rb").read(), check=False)
    if args.body is not None:
        base.body = open(args.body, encoding="utf-8").read().rstrip("\n")
    if args.greeting is not None:
        base.greeting = args.greeting
    if args.closing is not None:
        base.closing = args.closing
    if args.item is not None:
        base.attached_item = args.item
    base.serial = args.serial
    buf = base.build()
    open(args.out, "wb").write(buf)
    print("wrote %s (%#x bytes, serial %d, hash %s)"
          % (args.out, len(buf), args.serial, buf[MAIL_HASH:MAIL_HASH + HASH_LEN].hex()))
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("show", help="decode and verify a file")
    s.add_argument("file")
    s.set_defaults(func=cmd_show)

    s = sub.add_parser("sign", help="recompute the HMAC in place")
    s.add_argument("file")
    s.add_argument("-o", "--out")
    s.set_defaults(func=cmd_sign)

    s = sub.add_parser("bbs", help="build a forest_bbs file from text")
    s.add_argument("-t", "--text", help="UTF-8 text file (default: stdin)")
    s.add_argument("-s", "--serial", type=int, required=True,
                   help="dedup id; must differ from the last one the game saw")
    s.add_argument("-o", "--out", required=True)
    s.set_defaults(func=cmd_bbs)

    s = sub.add_parser("mail", help="build a forest_mail file from a template")
    s.add_argument("template", help="existing .bin to copy header fields from")
    s.add_argument("-b", "--body", help="UTF-8 text file for the letter body")
    s.add_argument("-g", "--greeting")
    s.add_argument("-c", "--closing")
    s.add_argument("-i", "--item", type=lambda x: int(x, 0),
                   help="attached item id, e.g. 0x3310 or 13072 "
                        "(default: keep the template's item)")
    s.add_argument("-s", "--serial", type=int, required=True)
    s.add_argument("-o", "--out", required=True)
    s.set_defaults(func=cmd_mail)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
