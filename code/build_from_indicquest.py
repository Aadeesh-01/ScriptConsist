"""
Build ScriptConsist-IQ: the short-answer factual subset of L3Cube-IndicQuest (EN + HI),
extended with Romanized Hindi.

Every one of the 200 source items gets an explicit KEEP (with short gold answer) or DROP
(with reason). Outputs:
  data/build/scriptconsist_iq.jsonl     kept items, in the ScriptConsist schema
  data/build/indicquest_filtering.csv   all 200 decisions, for the paper's data section

Source: Rohera et al. (2024), L3Cube-IndicQuest, CC BY-NC-SA 4.0.
"""

import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from romanize import romanize  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "indicquest"
SOURCE = {"title": "L3Cube-IndicQuest (Rohera et al., 2024)",
          "url": "https://github.com/l3cube-pune/indic-nlp/tree/main/L3Cube-IndicQuest"}

# idx: (gold, [variants incl. Devanagari], answer_type, locality, note)
G = "global"
I = "india"
KEEP = {
    0:   ("Bal Gangadhar Tilak", ["Tilak", "Lokmanya Tilak", "बाल गंगाधर तिलक", "तिलक"], "entity", I, ""),
    1:   ("Gopal Hari Deshmukh", ["Gopal Hari Deshmukh", "Deshmukh", "गोपाल हरि देशमुख"], "entity", I, ""),
    4:   ("Arun Jaitley", ["Jaitley", "अरुण जेटली", "जेटली"], "entity", I, "Piyush Goyal held interim charge briefly in 2019; Jaitley is the expected answer"),
    7:   ("Article 54", ["54", "Article 54", "अनुच्छेद 54"], "number", I, "Arts 54-55 both concern election; 54 is the standard answer"),
    8:   ("48", ["48", "forty-eight", "४८", "अड़तालीस"], "number", I, ""),
    13:  ("Allahabad High Court", ["Allahabad", "इलाहाबाद उच्च न्यायालय", "इलाहाबाद हाई कोर्ट", "इलाहाबाद"], "entity", I, ""),
    17:  ("Jammu and Kashmir", ["Jammu & Kashmir", "J&K", "Kashmir", "जम्मू और कश्मीर", "जम्मू-कश्मीर"], "entity", I, ""),
    21:  ("Bahujan Samaj Party", ["BSP", "Bahujan Samaj Party", "बहुजन समाज पार्टी", "बसपा"], "entity", I, "question asks 'outcome'; scored on winning party"),
    22:  ("Kulithalai", ["Kulithalai", "Kulitalai", "कुलीतलई", "कुलितलाई"], "entity", I, ""),
    27:  ("9", ["9", "nine", "९", "नौ"], "number", I, ""),
    29:  ("All India Trinamool Congress", ["TMC", "Trinamool", "Trinamool Congress", "AITC", "तृणमूल कांग्रेस", "तृणमूल"], "entity", I, "explicitly anchored 'as of 2024'; TMC in power since 2011"),
    30:  ("Government of India Act 1935", ["Government of India Act, 1935", "GOI Act 1935", "1935 Act", "भारत सरकार अधिनियम 1935"], "entity", I, ""),
    31:  ("Anandiben Patel", ["Anandiben", "Anandiben Patel", "आनंदीबेन पटेल", "आनंदीबेन"], "entity", I, ""),
    32:  ("Bharatiya Janata Party", ["BJP", "भारतीय जनता पार्टी", "भाजपा"], "entity", I, ""),
    33:  ("Bharatiya Janata Party", ["BJP", "भारतीय जनता पार्टी", "भाजपा"], "entity", I, ""),
    35:  ("Raj Thackeray", ["Raj Thackeray", "Raj Thakre", "राज ठाकरे"], "entity", I, "gold text truncated in source; verified externally"),
    38:  ("Partly Free", ["partly free", "आंशिक रूप से स्वतंत्र"], "entity", I, ""),
    45:  ("Oilseeds", ["oilseed", "oilseeds", "oil seeds", "तिलहन"], "entity", I, ""),
    46:  ("2nd", ["second", "2nd", "2", "दूसरा", "दूसरे"], "number", I, ""),
    48:  ("Mica", ["mica", "अभ्रक", "माइका"], "entity", I, ""),
    49:  ("Assam", ["Assam", "असम"], "entity", I, ""),
    53:  ("1972", ["1972", "Wildlife Protection Act 1972", "१९७२"], "year", I, ""),
    54:  ("Laterite soil", ["laterite", "लैटेराइट", "लेटराइट"], "entity", I, ""),
    55:  ("Ownership", ["ownership", "ownership of enterprises", "स्वामित्व"], "entity", I, ""),
    56:  ("Ahmedabad", ["Ahmedabad", "अहमदाबाद"], "entity", I, "Kanpur is sometimes called 'Manchester of the East'; Ahmedabad is the standard answer"),
    63:  ("Karnataka", ["Karnataka", "कर्नाटक"], "entity", I, ""),
    64:  ("Antarctica", ["Antarctica", "Antartica", "अंटार्कटिका"], "entity", G, ""),
    65:  ("Rajasthan", ["Rajasthan", "Sambhar", "राजस्थान", "सांभर"], "entity", I, ""),
    67:  ("Satopanth Glacier", ["Satopanth", "सतोपंथ"], "entity", I, ""),
    68:  ("Jhelum", ["Jhelum", "झेलम"], "entity", I, ""),
    69:  ("Abdul Kalam Island", ["Abdul Kalam Island", "Kalam Island", "Kalam Dweep", "अब्दुल कलाम द्वीप", "कलाम द्वीप"], "entity", I, "Hindi source answer reverses the relation (MT error)"),
    70:  ("Dachigam National Park", ["Dachigam", "दाचीगाम", "दाचिगाम"], "entity", I, ""),
    71:  ("1986", ["1986", "१९८६"], "year", I, ""),
    72:  ("Sedimentary rock", ["sedimentary", "तलछटी", "अवसादी"], "entity", G, ""),
    73:  ("49th parallel", ["49th parallel", "49 degrees north", "49°", "49वीं समानांतर", "49वां अक्षांश", "49"], "number", G, ""),
    74:  ("Tandi", ["Tandi", "तांडी", "टांडी"], "entity", I, ""),
    75:  ("Mars", ["Mars", "मंगल"], "entity", G, ""),
    76:  ("Indonesia", ["Indonesia", "इंडोनेशिया"], "entity", G, ""),
    78:  ("Djibouti", ["Djibouti", "जिबूती"], "entity", G, ""),
    80:  ("16,110 rupees", ["16110", "16,110", "१६११०"], "number", I, ""),
    82:  ("Ala-ud-Din Bahman Shah", ["Alauddin Bahman Shah", "Bahman Shah", "Hasan Gangu", "Alauddin Hasan Bahman Shah", "अलाउद्दीन बहमन शाह", "बहमन शाह", "हसन गंगू"], "entity", I, ""),
    85:  ("Ibrahim Adil Shah II", ["Ibrahim Adil Shah", "इब्राहीम आदिल शाह", "इब्राहिम आदिल शाह"], "entity", I, ""),
    86:  ("Balshastri Jambhekar", ["Bal Gangadhar Shastri Jambhekar", "Jambhekar", "बालशास्त्री जांभेकर", "जांभेकर"], "entity", I, ""),
    88:  ("Pratap Singh of Satara", ["Pratap Singh", "Pratapsinh", "Chhatrapati Pratap Singh", "प्रताप सिंह", "प्रतापसिंह"], "entity", I, "low-resource fact; keep, flag in error analysis"),
    90:  ("Majhi Janmathep", ["Mazi Janmathep", "Majhi Janmathep", "My Transportation for Life", "माझी जन्मठेप", "माझी जन्मथेप"], "entity", I, ""),
    91:  ("Sane Guruji", ["Sane Guruji", "Pandurang Sadashiv Sane", "साने गुरुजी"], "entity", I, ""),
    92:  ("Rukhmabai", ["Rukhmabai", "Rakhmabai", "Rukhmabai Raut", "रखमाबाई", "रुख्माबाई", "रुखमाबाई"], "entity", I, "source spells 'Rakhmabai Janardan Save'"),
    93:  ("Lala Lajpat Rai", ["Lajpat Rai", "लाला लाजपत राय", "लाजपत राय"], "entity", I, ""),
    95:  ("Lord Mountbatten", ["Mountbatten", "माउंटबेटन"], "entity", I, ""),
    97:  ("Aga Khan Palace", ["Aga Khan Palace", "Agha Khan Palace", "आगा खान पैलेस", "आगा खां महल", "आगा खान महल"], "entity", I, ""),
    98:  ("Constantinople", ["Constantinople", "Istanbul", "कांस्टेंटिनोपल", "कुस्तुंतुनिया", "इस्तांबुल"], "entity", G, ""),
    100: ("Baji Rao II", ["Bajirao II", "Baji Rao", "बाजी राव द्वितीय", "बाजीराव द्वितीय"], "entity", I, ""),
    101: ("Jamshedpur", ["Jamshedpur", "Sakchi", "Tatanagar", "जमशेदपुर", "साकची"], "entity", I, ""),
    102: ("Bal Gangadhar Tilak", ["Tilak", "Lokmanya Tilak", "बाल गंगाधर तिलक", "तिलक"], "entity", I, ""),
    103: ("Knighthood", ["knighthood", "knight", "Sir", "नाइटहुड", "नाइट"], "entity", I, ""),
    104: ("Appa Saheb", ["Appa Sahib", "Mudhoji II", "Mudhoji Bhonsle", "अप्पा साहेब", "मुधोजी"], "entity", I, "Hindi source mistranslates 'president' as राष्ट्रपति"),
    105: ("1803", ["1803", "१८०३"], "year", I, ""),
    106: ("1674", ["1674", "१६७४"], "year", I, ""),
    107: ("1601", ["1601", "१६०१"], "year", I, ""),
    108: ("Ahmad Shah Abdali", ["Abdali", "Ahmad Shah Durrani", "Durrani", "अहमद शाह अब्दाली", "अब्दाली", "दुर्रानी"], "entity", I, ""),
    109: ("Shivaji", ["Shivaji", "Chhatrapati Shivaji", "शिवाजी"], "entity", I, ""),
    110: ("First Anglo-Maratha War", ["First Anglo-Maratha", "प्रथम आंग्ल-मराठा", "पहला आंग्ल-मराठा"], "entity", I, ""),
    112: ("Ahmad Shah Bahmani", ["Ahmad Shah", "Ahmad Shah Wali", "अहमद शाह बहमनी", "अहमद शाह"], "entity", I, ""),
    113: ("Mundaka Upanishad", ["Mundaka", "Mundakopanishad", "मुण्डक", "मुंडक", "मुण्डकोपनिषद्"], "entity", I, ""),
    115: ("Ellora Caves", ["Ellora", "एलोरा"], "entity", I, ""),
    116: ("1929", ["1929", "December 1929", "१९२९"], "year", I, ""),
    117: ("Third Anglo-Maratha War", ["Third Anglo-Maratha", "तृतीय आंग्ल-मराठा", "तीसरा आंग्ल-मराठा"], "entity", I, ""),
    118: ("Civil Disobedience Movement", ["Civil Disobedience", "सविनय अवज्ञा"], "entity", I, ""),
    144: ("Ramayana", ["Ramayana", "Ramayan", "रामायण"], "entity", I, ""),
    146: ("Rabindranath Tagore", ["Tagore", "रवींद्रनाथ टैगोर", "रवीन्द्रनाथ ठाकुर", "टैगोर"], "entity", I, ""),
    153: ("Ilango Adigal", ["Ilango Adigal", "Ilango", "Ilango Adigalar", "इलांगो अडिगाल", "इलंगो अडिगल", "इलांगो"], "entity", I, "source calls it a 'novel'; it is an epic. Answer unaffected"),
    156: ("S. L. Bhyrappa", ["Bhyrappa", "SL Bhyrappa", "एस.एल. भैरप्पा", "भैरप्पा"], "entity", I, ""),
    170: ("Chennai", ["Chennai", "Madras", "चेन्नई", "मद्रास"], "entity", I, "Pune is also occasionally called this; Chennai is standard"),
    173: ("1950", ["1950", "१९५०"], "year", I, ""),
    174: ("Maharashtra", ["Maharashtra", "महाराष्ट्र"], "entity", I, "stable for decades; not explicitly dated"),
    175: ("NITI Aayog", ["NITI Aayog", "NITI", "नीति आयोग"], "entity", I, ""),
    178: ("6,000 rupees", ["6000", "6,000", "Rs 6000", "₹6,000", "६०००", "6 हजार", "छह हजार"], "number", I, ""),
    179: ("Excess reserves", ["excess reserves", "excess reserve", "अतिरिक्त रिज़र्व", "अतिरिक्त आरक्षित"], "entity", I, ""),
    185: ("Foreign Direct Investment", ["FDI", "foreign investment", "प्रत्यक्ष विदेशी निवेश", "विदेशी निवेश", "एफडीआई"], "entity", G, ""),
    187: ("1972", ["1972", "१९७२"], "year", I, "scheme 1972; the EGS Act followed in 1977"),
    195: ("Mixed economy", ["mixed", "mixed economy", "मिश्रित अर्थव्यवस्था", "मिश्रित"], "entity", I, ""),
}

DROP = {
    # reason codes: descriptive | multi_part | multi_answer | temporal | gold_error | gold_mismatch |
    #               ambiguous | contested | unverifiable | ill_posed | answer_leak
    2: "multi_part", 3: "descriptive", 5: "descriptive", 6: "multi_part", 9: "ambiguous",
    10: "multi_part", 11: "contested", 12: "temporal", 14: "descriptive", 15: "multi_part",
    16: "temporal", 18: "multi_answer", 19: "temporal", 20: "temporal", 23: "contested",
    24: "ambiguous", 25: "multi_answer", 26: "multi_answer", 28: "ambiguous", 34: "ambiguous",
    36: "descriptive", 37: "descriptive", 39: "multi_answer", 40: "descriptive", 41: "descriptive",
    42: "gold_mismatch", 43: "gold_mismatch", 44: "gold_error", 47: "descriptive", 50: "contested",
    51: "multi_answer", 52: "descriptive", 57: "temporal", 58: "multi_part", 59: "multi_answer",
    60: "multi_answer", 61: "multi_answer", 62: "ambiguous", 66: "ill_posed", 77: "ill_posed",
    79: "ambiguous", 81: "multi_part", 83: "multi_part", 84: "descriptive", 87: "gold_error",
    89: "gold_error", 94: "ambiguous", 96: "multi_answer", 99: "ambiguous", 111: "multi_answer",
    114: "descriptive", 119: "descriptive", 126: "gold_error", 127: "descriptive", 128: "descriptive",
    143: "contested", 145: "descriptive", 147: "descriptive", 148: "descriptive", 149: "ambiguous",
    150: "unverifiable", 151: "unverifiable", 152: "descriptive", 154: "ambiguous",
    155: "descriptive", 172: "ill_posed", 176: "descriptive", 177: "ambiguous", 180: "descriptive",
    171: "answer_leak", 181: "ill_posed", 182: "multi_answer", 183: "gold_error", 184: "multi_answer", 186: "gold_error",
    188: "descriptive", 189: "multi_part", 190: "temporal", 191: "descriptive", 192: "descriptive",
    193: "multi_answer", 194: "temporal", 196: "descriptive", 197: "multi_part", 198: "gold_error",
    199: "descriptive",
}
DROP.update({i: "descriptive" for i in [120, 121, 122, 123, 124, 125, 129, 130, 131, 132, 133,
                                        134, 135, 136, 137, 138, 139, 140, 141, 142, 157, 158,
                                        159, 160, 161, 162, 163, 164, 165, 166, 167, 168, 169]})

DROP_NOTES = {
    44: "India is not the leading tea producer (China) or exporter",
    50: "Chota Nagpur Plateau is usually called the richest mineral belt",
    87: "body was the Planning Commission, not 'Planning Board'",
    89: "Gokhale founded the Servants of India Society (1905); Bharat Sevak Samaj is 1952",
    94: "'Provisional Government of India' also names the 1915 Kabul government",
    96: "both Maharashtra and Gujarat were formed on 1 May 1960",
    26: "Kerala, West Bengal and Tripura all elected communist governments",
    183: "agriculture, not services, is India's largest employer",
    198: "savings rates deregulated in 2011; banks set them",
    126: "gold answer does not match the novel",
    11: "seat counts for 'Janata Party and allies' differ across sources",
    171: "Hindi MT renders ad valorem as मूल्यानुसार ('according to value'), leaking the answer in Devanagari only",
    151: "could not verify a Marathi novel 'Manini' or its author",
}


def main():
    en = list(csv.DictReader(open(RAW / "English.csv", encoding="utf-8")))
    hi = list(csv.DictReader(open(RAW / "Hindi.csv", encoding="utf-8")))
    assert len(en) == len(hi) == 200
    assert set(KEEP) | set(DROP) == set(range(200)), sorted(set(range(200)) - set(KEEP) - set(DROP))
    assert not set(KEEP) & set(DROP)

    items, log = [], []
    for i, (e, h) in enumerate(zip(en, hi)):
        dom = e["Domain"].strip()
        if i in DROP:
            log.append({"iq_index": i, "domain": dom, "decision": "drop", "reason": DROP[i],
                        "note": DROP_NOTES.get(i, ""), "question_en": e["Question"].strip()})
            continue
        gold, variants, atype, loc, note = KEEP[i]
        hi_q = " ".join(h["Question"].split())
        items.append({
            "id": f"iq_{i:03d}",
            "iq_index": i,
            "domain": dom,
            "locality": loc,
            "answer_type": atype,
            "en": " ".join(e["Question"].split()),
            "hi_dev_mt": hi_q,          # Google-Translate output from IndicQuest, unedited
            "hi_dev": "",               # human post-edited Devanagari (annotator fills)
            "hi_rom_natural": "",       # human-typed Romanized Hindi (annotator fills)
            "hi_rom_std": romanize(hi_q),  # regenerated from hi_dev after post-editing
            "gold_answer": gold,
            "gold_variants": variants,
            "sources": [SOURCE],
            "gold_source_answer_en": " ".join(e["Answer"].split()),
            "provenance": "indicquest",
            "status": "candidate",
            "notes": note,
        })
        log.append({"iq_index": i, "domain": dom, "decision": "keep", "reason": "",
                    "note": note, "question_en": e["Question"].strip()})

    out = ROOT / "data" / "build" / "scriptconsist_iq.jsonl"
    out.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in items) + "\n", encoding="utf-8")
    with open(ROOT / "data" / "build" / "indicquest_filtering.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(log[0].keys()))
        w.writeheader()
        w.writerows(log)

    from collections import Counter
    print(f"kept {len(items)} / 200")
    print("kept by domain:", dict(Counter(x["domain"] for x in items)))
    print("kept by locality:", dict(Counter(x["locality"] for x in items)))
    print("kept by type:", dict(Counter(x["answer_type"] for x in items)))
    print("drop reasons:", dict(Counter(DROP.values()).most_common()))


if __name__ == "__main__":
    main()
