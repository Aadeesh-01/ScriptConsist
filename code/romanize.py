"""
Deterministic Devanagari -> practical Roman transliteration for Hindi (hi_rom_std).

Pipeline: Aksharamukha IAST with Hindi schwa deletion, then a fixed ASCII mapping
that approximates common informal spelling (no diacritics, 'sh', 'ch', 'chh', 'd' for ड़).
Same input always gives the same output, so this is the reproducible Romanized condition.
"""

import re
import unicodedata

from aksharamukha import transliterate

# Applied in order, on IAST output (before diacritics are stripped)
_PRE = [
    ("r̤h", "dh"), ("r̤", "d"),        # ढ़ ड़ -> dh d  (ladai, padhai)
    ("ṛ", "ri"), ("ṝ", "ri"),         # ऋ
    ("ś", "sh"), ("ṣ", "sh"),         # श ष
    ("ch", "\x00"), ("c", "ch"), ("\x00", "chh"),   # च -> ch, छ -> chh
    ("ṃ", "n"), ("ṁ", "n"), ("ṅ", "n"), ("ñ", "n"),
    ("ḥ", "h"),
]


def romanize(text: str) -> str:
    iast = transliterate.process("Devanagari", "IAST", text, pre_options=["RemoveSchwaHindi"])
    for a, b in _PRE:
        iast = iast.replace(a, b)
    # strip remaining diacritics: ā->a, ī->i, ṭ->t, ḍ->d, ṇ->n ...
    out = "".join(c for c in unicodedata.normalize("NFD", iast) if not unicodedata.combining(c))
    out = re.sub(r"\s+", " ", out).strip()
    return out[:1].upper() + out[1:] if out else out


if __name__ == "__main__":
    for s in ["पानीपत की तीसरी लड़ाई में मराठों को किसने हराया?",
              "भारत का सबसे पुराना तेल उत्पादक राज्य कौन सा है?",
              "किस शहर को भारत का मैनचेस्टर कहा जाता है?",
              "छत्रपति शिवाजी महाराज का राज्याभिषेक किस वर्ष हुआ था?",
              "कौन सी मिट्टी तीव्र निक्षालन से बनती है"]:
        print(romanize(s))
