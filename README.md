# ACWW "axmail" WFC download files

Format documentation and an experimental writer for the two files Animal
Crossing: Wild World (NDS, **ADME**, USA Rev 1) fetched from Nintendo WFC:

```
http://axing.nintendowifi.net/axmail/forest_bbs_USA.bin?brid=ADME30io38k
http://axing.nintendowifi.net/axmail/forest_mail_USA.bin?brid=ADME30io38k
```

`forest_bbs` is the town bulletin-board message; `forest_mail` is a letter
delivered to the player's mailbox. Both are fixed-size and authenticated.

## The hash

```
hash = HMAC-MD5(key = b"HNANKTMSYNKASSNK",
                msg = <entire file, with the 16 hash bytes zeroed>)
```

| file | size | serial | hash | notes |
|---|---|---|---|---|
| `forest_bbs_USA.bin` | `0xD2` | u16 @ `0xC0` | `0xC2`..`0xD1` | — |
| `forest_mail_USA.bin` | `0x108` | u16 @ `0xF4` | `0xF6`..`0x105` | u16 pad @ `0x106` |

Three things that are easy to get wrong:

- The key is a **16-byte ASCII string with no NUL**, used as an HMAC key (not a
  salt, and not concatenated with the message).
- The message is the **whole fixed-size file**, not the bytes before the hash.
- The hash field must be **zeroed** before hashing, not excised.

The hostname and the `brid` are *not* part of the hash — they only build the
request URL.

## The serial is a dedup id, not a checksum

Both files carry a `u16` immediately before the hash. On receipt the game
compares it against the last value it stored and **silently discards the file if
they are equal**. A replacement file must use a different serial than the one
the console last accepted, or nothing will happen and the hash will not be the
reason. Retail values: BBS 50, mail 110.

## Text encoding

Not ASCII — the game's own single-byte table:

| range | meaning |
|---|---|
| `0x00` | NUL / padding |
| `0x01`–`0x1A` | `A`–`Z` |
| `0x1B`–`0x34` | `a`–`z` |
| `0x35`–`0x3E` | `0`–`9` |
| `0x85` | space |
| `0x86` | newline |
| `0x87` | `!` |
| `0x92` | `,` |
| `0x94` | `.` |
| `0xB1` | `'` |

Full 256-entry table in [`ww_charset.py`](ww_charset.py), transcribed from
[ACSE](https://github.com/Cuyler36/ACSE) (`ACSE.Core/Utilities/StringUtility.cs`,
`WwCharacterDictionary`). ACSE notes that some of the high accented slots may
still be wrong; the ASCII-range entries are exercised by both retail files here
and decode cleanly.

## Files

| file | what |
|---|---|
| `acww_forest_bbs.ksy` | Kaitai Struct definition for the bulletin board file |
| `acww_forest_mail.ksy` | Kaitai Struct definition for the letter file |
| `ww_charset.py` | 256-entry character table + reverse map |
| `axmail.py` | parse / decode / build / sign, library + CLI |
| `test_roundtrip.py` | parse+rebuild each retail file, require byte-identical |
| `test_ksy.py` | check the .ksy layouts tile each file exactly |
| `compile_ksy.js` | run the real Kaitai compiler over both .ksy |
| `extract_save_letters.py` | pull letters out of ACWW save files |

The `.ksy` files compile clean with the official Kaitai Struct compiler
(v0.11.0) for all 13 supported targets — python, javascript, java, csharp,
cpp_stl, go, rust, php, ruby, perl, lua, nim, html — and the generated Python
parsers were run against both retail files, producing output identical to
`axmail.py`. Kaitai cannot express the character table, so text fields are left
as raw byte arrays; decode them with `ww_charset.py`.

## Usage

```bash
python3 axmail.py show ~/Downloads/forest_bbs_USA.bin
```

```bash
python3 axmail.py bbs -t message.txt -s 51 -o forest_bbs_USA.bin
```

Letters are built by editing an existing file, which is the safe route while
parts of the header are still unidentified:

```bash
python3 axmail.py mail ~/Downloads/forest_mail_USA.bin -b body.txt -s 111 -o forest_mail_USA.bin
```

Attach a gift item with `-i/--item` (decimal or `0x` hex, e.g. `0x3310` for the
Lawn Chair); omitted, the template's item is kept as-is:

```bash
python3 axmail.py mail ~/Downloads/forest_mail_USA.bin -b body.txt -i 0x3310 -s 111 -o forest_mail_USA.bin
```

`sign` recomputes the HMAC of a file you edited by other means:

```bash
python3 axmail.py sign forest_mail_USA.bin
```

Tests:

```bash
python3 test_roundtrip.py && python3 test_ksy.py
```

Compiling the Kaitai definitions needs no JVM — the compiler has a JS build:

```bash
npm install kaitai-struct-compiler js-yaml && node compile_ksy.js
```

```bash
node compile_ksy.js -o generated python
```

## Confidence

Verified byte-exact:

- both file sizes, the serial offsets, the hash offsets and the HMAC scheme
  (derived from the game's own verifier, then confirmed against both retail
  files);
- parse → rebuild is byte-identical for both retail files.

Established from save-file evidence (194 well-formed letters across 18 saves,
see below):

```
0x04 ref   recipient_town     id 0xC1BD "Redmond"
0x0E ref   recipient_player   id 0x5C04 (blank name)
0x1C ref   sender_town        id 0xC1BD "Redmond"
0x26 ref   sender_player      id 0x81D4 "Nintendo"
0xF0 u16   attached_item      0x13DF   (0xFFF1 = none)
```

A "ref" is `u16 id` + `char name[8]`. The ids are per-town/per-player values,
not fixed constants — saves holding genuine Nintendo letters use different ids
(62097/63945) for the same "Redmond"/"Nintendo" names.

Still **not** identified — characterised only by observed distributions:

```
0x00 u32   unk_00     0        (every sampled letter)
0x18 u16   unk_18     0        (158/194; 1 in 22)
0x1A u16   unk_1a     3        (delivered letters show 2 -> rewritten on delivery)
0x30 u16   unk_30     1        (delivered letters show 0 -> rewritten on delivery)
0x32 u16   unk_32     2        (4:80, 2:72, 0:25, 3:17)
0xEC u8[4] unk_ec     05 35 42 11   (first byte 5 in most letters)
0xF2 u16   unk_f2     0        (174/194)
```

All of these sit inside the hashed region, so they must be byte-correct even
while their meaning is unknown; that is why the `mail` subcommand copies them
from a template.

## Save-file evidence

Letters live in ACWW saves as the same 0xF4 struct, stored back-to-back at
exactly 0xF4 stride. `extract_save_letters.py` finds them by locating the
encoded greeting "Dear" and backing up 0x34 bytes:

```bash
python3 extract_save_letters.py --fields /path/to/*.sav
```

The sender/recipient direction comes from the sign-off text: among letters where
both player names are non-blank, the closing names the 0x1C/0x26 pair in 10
cases and the 0x04/0x0E pair in **0**. (Per-save constancy does *not* work as a
test — a save also stores letters the player wrote, so neither pair is constant
across a whole save.)

Those saves also contain genuine delivered WFC letters, which are directly
comparable to this download format — senders "Nintendo" of "Redmond" and
"S. Iwata" of "Redmond", with the same `Dear ,` blank-name greeting. Comparing
them to the axmail file is what showed `unk_1a` and `unk_30` differ between the
downloaded and the delivered copy, i.e. the game rewrites them on delivery.

Public saves for this are on
[GameFAQs](https://gamefaqs.gamespot.com/ds/920786-animal-crossing-wild-world/saves)
(Action Replay `.duc`/`.dst`; the 500-byte AR header is harmless, the scan is
offset-independent).

## ROM reference (ADME, USA Rev 1)

True **runtime** addresses:

| address | what |
|---|---|
| `0x0209EC80` | BBS verify routine (Thumb) |
| `0x0209ECF8` | mail verify routine (Thumb) |
| `0x02000B7C` | key getter → `0x02000B6C` = `"HNANKTMSYNKASSNK"` |
| `0x0203EC4C` | returns `base + 0xC2` (BBS hash offset) |
| `0x0203ECC8` | returns `base + 0xF6` (mail hash offset) |
| `0x0203EC18` | BBS accept path (serial dedup) |
| `0x0203EC58` | mail accept path (serial dedup) |
| `0x0211A748` | `hmac_md5(out, msg, msglen, key, keylen)` |
| `0x0211AE74` / `0x0211AD80` / `0x0211ACBC` | MD5 Init / Update / Final |
| `0x0209EE60` | BBS downloader (builds URL, size `0xD2`) |
| `0x020E9B00` | brid builder (copies 12 bytes = `"ADME30io38k"` + NUL) |

### Ghidra address gotcha

Ghidra's NDS loader maps the decompressed ARM9 flat at `0x02000000`, but
everything from `autoload_start = 0x020E7500` onward is autoload **image** data,
not code at its runtime address:

| autoload | ram | size | image (Ghidra addr) |
|---|---|---|---|
| 0 | `0x01FF8000` (ITCM) | `0x5AE0` | `0x020E7500` |
| 1 | `0x027E0000` (DTCM) | `0x0460` | `0x020ECFE0` |
| 2 | `0x020E7500` (main) | `0x551C0` | `0x020ED440` |

So **main-RAM code above Ghidra `0x020ED440` is `0x5F40` higher than its true
runtime address**. Add `0x5F40` to the table above to look these up in an
as-imported project. The classic symptom is `blx 0x020E9E38` appearing to land
in fixed-point matrix math — that is really ITCM content shown at the wrong
address. To fix it properly, decompress the ARM9 (BLZ) and parse ModuleParams
(magic `DEC00621 2106C0DE`) to place the autoload blocks at their real
addresses.

## Credits

- The 256-entry Wild World character table is transcribed from
  [ACSE](https://github.com/Cuyler36/ACSE) by Cuyler36
  (`ACSE.Core/Utilities/StringUtility.cs`, `WwCharacterDictionary`).
- The letter-structure field mapping was derived from public save files
  uploaded to [GameFAQs](https://gamefaqs.gamespot.com/ds/920786-animal-crossing-wild-world/saves)
  by their respective contributors.
- Struct definitions are written for
  [Kaitai Struct](https://kaitai.io/).

## License

MIT. See [LICENSE](LICENSE).

Copyright (c) 2026 quatric
