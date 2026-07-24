meta:
  id: acww_forest_bbs
  title: Animal Crossing - Wild World, WFC bulletin-board download (forest_bbs_*.bin)
  file-extension: bin
  endian: le
  license: MIT

doc: |
  The town bulletin-board message that Animal Crossing: Wild World (NDS, ADME)
  downloaded from Nintendo WFC:

      http://axing.nintendowifi.net/axmail/forest_bbs_USA.bin?brid=ADME30io38k

  The file is a fixed 0xD2 bytes -- the game hardcodes that length and copies
  exactly that many bytes into a stack buffer before validating.

  AUTHENTICATION
  The trailing 16 bytes are an HMAC-MD5 over the *entire* 0xD2-byte file with
  those same 16 bytes zeroed:

      hash = HMAC-MD5(key = "HNANKTMSYNKASSNK",       # 16 ASCII bytes, no NUL
                      msg = file with [0xC2..0xD2) set to 0x00)

  Verifier at ARM9 0x0209EC80; key getter 0x02000B7C; HMAC-MD5 at 0x0211A748.
  (Those are true runtime addresses -- see README.md, Ghidra's flat ARM9 map is
  offset by +0x5F40 above 0x020ED440.)

  TEXT ENCODING
  `text` is not ASCII.  It uses the game's own single-byte table:
  0x00 NUL/pad, 0x01-0x1A "A".."Z", 0x1B-0x34 "a".."z", 0x35-0x3E "0".."9",
  0x85 space, 0x86 newline, 0x87 "!", 0x92 ",", 0x94 ".", 0xB1 apostrophe.
  Kaitai cannot express this table, so the field is left as raw bytes; use
  ww_charset.py from this directory to decode it.

seq:
  - id: text
    size: 0xc0
    doc: |
      Bulletin-board message in Wild World character encoding, NUL-padded to
      0xC0 bytes.  0x86 acts as a line break.

  - id: serial
    type: u2
    doc: |
      Dedup id.  On receipt the game compares this against the last value it
      stored (ARM9 0x0203EC18); if they are equal the message is silently
      discarded, otherwise the value is saved and the message posted.  A
      replacement file therefore MUST use a different serial than the one the
      console last accepted.  Retail sample: 50.

  - id: hash
    size: 16
    doc: HMAC-MD5 as described above.  Zero this field to recompute.
