meta:
  id: acww_forest_mail
  title: Animal Crossing - Wild World, WFC letter download (forest_mail_*.bin)
  file-extension: bin
  endian: le
  license: CC0-1.0

doc: |
  The letter that Animal Crossing: Wild World (NDS, ADME) downloaded from
  Nintendo WFC and delivered to the player's mailbox:

      http://axing.nintendowifi.net/axmail/forest_mail_USA.bin?brid=ADME30io38k

  Fixed 0x108 bytes -- the game hardcodes that length.

  The first 0xF4 bytes are the game's ordinary letter structure: in a save file,
  letters are stored back-to-back at exactly 0xF4 stride.  The download format
  simply appends a serial and an HMAC to it.

  AUTHENTICATION
  Identical scheme to forest_bbs, only the offset differs:

      hash = HMAC-MD5(key = "HNANKTMSYNKASSNK",
                      msg = file with [0xF6..0x106) set to 0x00)

  Verifier at ARM9 0x0209ECF8; key getter 0x02000B7C; HMAC-MD5 at 0x0211A748.

  TEXT ENCODING
  All char fields use the Wild World single-byte table, not ASCII:
  0x00 NUL/pad, 0x01-0x1A "A".."Z", 0x1B-0x34 "a".."z", 0x35-0x3E "0".."9",
  0x85 space, 0x86 newline, 0x87 "!", 0x92 ",", 0x94 ".", 0xB1 apostrophe.
  Decode with ww_charset.py from this directory.

  CONFIDENCE
  Offsets and sizes are confirmed (parse + rebuild is byte-exact on the retail
  USA file; the hash and serial offsets come from the game's own code).

  The sender/recipient direction was established from 213 letters extracted from
  18 GameFAQs save files: among letters where both player names are non-blank,
  the "From X" closing text names the pair at 0x1C/0x26 in 10 of 12 cases and
  the pair at 0x04/0x0E in 0 cases.  (A save also holds letters the player
  *wrote*, so neither pair is constant across a whole save -- the closing-text
  correlation, not per-save constancy, is what fixes the direction.)

  Fields still named `unk_*` are characterised by observed value distributions
  but not identified.

seq:
  - id: unk_00
    type: u4
    doc: Zero in the retail sample and in 194/213 sampled letters.

  - id: recipient_town
    type: name_ref
    doc: |
      Town the letter is addressed to.  Retail axmail: id 0xC1BD, "Redmond" --
      a placeholder copy of the sender's town, since a WFC broadcast has no
      specific recipient town.

  - id: recipient_player
    type: name_ref
    doc: |
      Player the letter is addressed to.  Retail axmail: id 0x5C04, name BLANK
      -- the greeting is "Dear ," and the game fills the name in on delivery.

  - id: unk_18
    type: u2
    doc: Zero in the retail sample; 0 in 158/213 and 1 in 22/213 sampled letters.

  - id: unk_1a
    type: u2
    doc: |
      Small enum.  Retail axmail: 3.  Delivered Nintendo letters found in saves
      all show 2, so the game appears to rewrite this on delivery.  Sampled
      distribution: 2 (106), 3 (57), 0 (26), 7 (7).

  - id: sender_town
    type: name_ref
    doc: |
      Town the letter is from.  Varies letter-to-letter within a save.  Retail
      axmail: id 0xC1BD, "Redmond" -- Nintendo of America's home city.
      Delivered WFC letters in real saves show "Redmond" and "Japan" here.

  - id: sender_player
    type: name_ref
    doc: |
      Player the letter is from.  Retail axmail: id 0x81D4, "Nintendo".
      Delivered WFC letters in real saves show "Nintendo" and "S. Iwata".
      The ids are per-town/per-player values, not fixed constants: saves holding
      genuine Nintendo letters use different ids (62097 / 63945) than this file.

  - id: unk_30
    type: u2
    doc: |
      Retail axmail: 1.  Delivered Nintendo letters in saves show 0, so this is
      also rewritten on delivery.  Sampled: 0 (168), 1 (22).

  - id: unk_32
    type: u2
    doc: 'Small enum. Retail axmail: 2. Sampled: 4 (80), 2 (76), 0 (34), 3 (17).'

  - id: greeting
    size: 0x18
    doc: 'Salutation, NUL-padded. Retail: "Dear ," (name filled in by the game).'

  - id: body
    size: 0x80
    doc: Letter body, NUL-padded.  0x86 acts as a line break.

  - id: closing
    size: 0x20
    doc: 'Sign-off, NUL-padded. Retail: "From Nintendo".'

  - id: unk_ec
    size: 4
    doc: |
      Retail axmail: 05 35 42 11.  The first byte is 5 in 162/213 sampled
      letters; the remaining three vary.  Not identified.

  - id: attached_item
    type: u2
    doc: |
      Item enclosed with the letter.  0xFFF1 is Wild World's "empty item"
      sentinel and accounts for 90/213 sampled letters (no attachment); the
      remainder carry varied plausible item ids.  Retail axmail: 0x13DF -- the
      WFC letter did ship a present.

  - id: unk_f2
    type: u2
    doc: Zero in the retail sample and in 174/213 sampled letters.

  - id: serial
    type: u2
    doc: |
      Dedup id.  The game compares this against a stored value (ARM9
      0x0203EC58) and discards the letter if they match, so a replacement file
      MUST use a different serial than the one last accepted.  Retail: 110.

  - id: hash
    size: 16
    doc: HMAC-MD5 as described above.  Zero this field to recompute.

  - id: pad
    type: u2
    doc: Zero in the retail sample; inside the hashed region, so it must be right.

types:
  name_ref:
    doc: |
      The game's "who" reference: a 16-bit id followed by an 8-byte name in Wild
      World character encoding (NUL-padded, and NOT NUL-terminated when the name
      fills all 8 characters, e.g. "Nintendo").
    seq:
      - id: id
        type: u2
      - id: name
        size: 8
