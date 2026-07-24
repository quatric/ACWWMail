"""Animal Crossing: Wild World (English/USA) character table.

Index = in-game byte value, value = Unicode string.  Empty string means the
slot is unmapped/unknown.  Table transcribed from ACSE
(Cuyler36/ACSE, ACSE.Core/Utilities/StringUtility.cs, WwCharacterDictionary);
ACSE notes that a few of the high/accented slots may still be wrong.

Notable: 0x00 NUL/pad, 0x01-0x1A "A"-"Z", 0x1B-0x34 "a"-"z",
0x35-0x3E "0"-"9", 0x85 space, 0x86 newline, 0x87 "!", 0xB1 apostrophe.
"""

CHARS = [
    '\x00', 'A', 'B', 'C', 'D', 'E', 'F', 'G',
    'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O',
    'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W',
    'X', 'Y', 'Z', 'a', 'b', 'c', 'd', 'e',
    'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm',
    'n', 'o', 'p', 'q', 'r', 's', 't', 'u',
    'v', 'w', 'x', 'y', 'z', '0', '1', '2',
    '3', '4', '5', '6', '7', '8', '9', '⨍',
    's̊', 'Œ', 'Ž', 'š', 'œ', 'ž', 'Ÿ', 'À',
    'Á', 'Â', 'Ã', 'Ä', 'Å', 'Æ', 'Ç', 'È',
    'É', 'Ê', 'Ë', 'Ì', 'Í', 'Î', 'Ï', 'Đ',
    'Ñ', 'Ò', 'Ó', 'Ô', 'Õ', 'Ö', 'Ø', 'Ù',
    'Ú', 'Û', 'Ü', 'Ý', 'Þ', 'ß', 'à', 'á',
    'â', 'ã', 'ä', 'å', 'æ', 'ç', 'è', 'é',
    'ê', 'ë', 'ì', 'í', 'î', 'ï', 'ð', 'ñ',
    'ò', 'ó', 'ô', 'õ', 'ö', 'ø', 'ù', 'ú',
    'û', 'ü', 'ý', 'þ', 'ÿ', ' ', '\n', '!',
    '“', '#', '$', '%', '&', '´', '(', ')',
    '*', '+', ',', '-', '.', '/', ':', ';',
    '<', '=', '>', '?', '@', '[', '{', ']',
    '|', '_', '}', '、', '˷', '…', '~', '£',
    '†', '‡', '^', '‰', '⟨', '`', '”', '•',
    '‒', "'", '—', '"', '™', '⟩', '\u2001', '˜',
    '¥', '╎', '§', '¡', '¢', '£', '¨', '©',
    'ª', '«', '¬', '–', '®', '°', '±', '²',
    '³', '‾', 'ˢ', 'µ', '¶', '→', '¹', 'º',
    '»', '･', '¼', '½', '¾', '', '', '',
    '', '¿', '×', '÷', '💧', '★', '❤', '♪',
    '', '', '', '', '', '', '', '',
    '', '', '', '', '', '', '', '',
    '', '', '', '', '', '', '', '',
    '', '', '', '', '', '', '', '',
]

assert len(CHARS) == 256

# char -> byte, lowest byte wins when a glyph appears more than once
ENCODE = {}
for _i, _c in enumerate(CHARS):
    if _c and _c not in ENCODE:
        ENCODE[_c] = _i

