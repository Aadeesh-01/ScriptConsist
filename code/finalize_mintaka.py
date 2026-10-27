"""
Merge annotator A's work into the Mintaka sample and apply the review decisions.

Inputs:  data/build/scriptconsist_mk.jsonl, data/annotations/annotations_final.jsonl
Outputs: data/build/scriptconsist_mk_v1.jsonl   (all 300, with status accepted / rejected / needs_retype)
         data/build/mintaka_review.csv          (one row per non-accepted item, with reason)

Keys are positions in scriptconsist_mk.jsonl (0-based), which match "Question N" on the
annotation page as N-1.
"""

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Annotator marked the gold wrong and gave a verified correction -> keep with new gold
ANNOTATOR_GOLD_FIX = {
    "mk_07e9be09": ("1999", ["1999"]),                                   # Super Smash Bros (original)
    "mk_4f4d5130": ("2005", ["2005", "Batman Begins"]),                  # first Nolan Batman
    "mk_65bc344c": ("1980", ["1980"]),                                   # Michael Jackson first Grammy
    "mk_93f33a0d": ("Lorde", ["Lorde", "लॉर्ड"]),                          # youngest Song of the Year
}
# Annotator marked wrong/unsure, or dropped -> reject (reason)
ANNOTATOR_REJECT = {
    "mk_146dcc1f": "ambiguous: 'of 1998' = 1998 ceremony (Titanic) or 1998 films (Saving Private Ryan)",
    "mk_3d62451a": "ambiguous: Guinness record (Swearnet) vs mainstream film (Wolf of Wall Street)",
    "mk_4fbea042": "ambiguous: singles/doubles, Open era or not (Rosewall, Navratilova, Federer)",
    "mk_850350fa": "sources disagree on founding year (1953-1955)",
    "mk_c4a28e45": "record changed in 2025 (Biden -> Trump)",
    "mk_ca177b71": "gold wrong, correct answer not established",
    "mk_d0b0a826": "ambiguous: depends on counting expansions",
    "mk_fad7814e": "time-sensitive ('last')",
    "mk_2ea25114": "annotator unsure, dropped",
    "mk_8f65c610": "ambiguous: total (USA) vs per capita (Finland)",
    "mk_a0b5207f": "no single record holder",
    "mk_5b4c75ff": "ambiguous: Augustus vs Eastern emperors (Theodosius II)",
    "mk_6d4d9f3d": "two answers: Norway and Germany tied on golds",
    "mk_9905b547": "subjective ('biggest')",
    "mk_ad44b342": "multiple answers: Super, The Suicide Squad, Superman",
    "mk_f603cfc1": "multiple answers; Inuit are not First Nations",
}
# Reviewer (Claude) decisions on items the annotator marked correct, by position
REVIEW_REJECT = {
    2: "ambiguous: started writing 1990, published 1997",
    23: "two adaptations: Swedish (Nyqvist) and US (Craig)",
    33: "vague ('most awards')",
    35: "contradicts item 36; page counts vary by edition",
    36: "contradicts item 35; page counts vary by edition",
    44: "two answers: Venice and Amsterdam",
    45: "census rank changes over time",
    52: "ambiguous: Shanghai vs Chongqing (municipality); Hinglish also omits 'China'",
    61: "two answers: Everest is on the Nepal-China border (Kathmandu / Beijing)",
    64: "record changed: Melbourne overtook Sydney (2023, ABS)",
    67: "record changed: Melbourne vs Sydney (2023)",
    68: "sources disagree (Mackenzie, Yukon, Rio Grande)",
    74: "gold doubtful: most meteorites are found in Antarctica",
    75: "record changed: India passed China in 2023",
    76: "contested: Egypt vs Persia",
    83: "ambiguous: advisers 1955 vs combat troops 1965",
    105: "ill-posed question",
    114: "vague ('affiliation')",
    125: "ambiguous: 2020 ceremony vs 2020 films",
    127: "ambiguous: academy founded 1947, first awards 1949",
    150: "box-office record can change",
    153: "garbled question",
    178: "ambiguous: Zanzibar (then) vs Tanzania (now)",
    182: "ambiguous: award year 1991 vs ceremony 1992",
    185: "view-count record can change",
    194: "ambiguous: King Salman (head of state) vs MBS (PM)",
    234: "two answers: Cowboys and Broncos",
    236: "ambiguous: Feb 2020 game vs 2020 season",
    241: "time-sensitive ('last year')",
    244: "ill-posed: World Cups are four years apart",
    245: "no longer true (Henderson left Liverpool in 2023)",
    246: "two answers: Michael Jordan and Charles Barkley",
    249: "coach changes over time",
    261: "contested after doping disqualifications",
    265: "ambiguous: released 31 Dec 1996 (NA) vs 1997",
    267: "ambiguous: early access 2015 vs full release 2017",
    287: "time-sensitive ('last')",
    296: "sales record can change",
    212: "Hinglish asks who the president was; the question asks for his party (not retyped)",
    # near-duplicates (keep the first occurrence)
    31: "duplicate of 27", 32: "duplicate of 27", 37: "duplicate of 34", 170: "duplicate of 155",
    291: "duplicate of 270", 292: "duplicate of 274", 299: "duplicate of 297",
}
REVIEW_GOLD_FIX = {
    1: ("Shot by George", ["shot", "gunshot", "George shot him", "shot in the head", "गोली"]),
    248: ("Tottenham Hotspur", ["Tottenham", "Spurs", "टोटेनहम"]),   # gold named the player, question asks the team
}
REVIEW_ADD_VARIANTS = {
    53: ["Colombia", "कोलंबिया"],
    233: ["Staples Center"],          # renamed in 2021; older models know the old name
    269: ["Soviet Union", "USSR", "सोवियत संघ"],
}
# Hinglish changed the meaning -> annotator retyped on 2026-10-26 (all done except 212, rejected above)
NEEDS_RETYPE = {}
RETYPED = {
    48: "says the city was put on trial; should be the city where the trials were held",
    94: "'first women' should be 'first lady'",
    98: "'ke bade' (after) should be 'se pehle' (before)",
    117: "leaves out Hagrid / Harry Potter, so it can't be answered",
    130: "asks for the director; the question asks for the movie",
    201: "'Georgina' should be 'Georgia'",
    212: "asks who the president was; the question asks for his party",
    231: "'20212' should be '2012'",
    279: "written fully in English; needs Hinglish",
}


def main():
    items = [json.loads(l) for l in open(ROOT / "data" / "build" / "scriptconsist_mk.jsonl", encoding="utf-8")]
    ann = {}
    for l in open(ROOT / "data" / "annotations" / "annotations_final.jsonl", encoding="utf-8"):
        a = json.loads(l)
        ann[a["item"]] = a
    rows = []
    for k, it in enumerate(items):
        a = ann[it["id"]]
        it["hi_dev"] = a.get("hi_dev") or it["hi_dev_pro"]
        it["hi_rom_natural"] = a["hi_rom_natural"]
        it["annotation"] = {"annotator": "A", "gold_ok": a.get("gold_ok"), "gold_fix_or_source": a.get("gold_fix", ""),
                            "hi_dev_changed": a.get("hi_dev_changed", False), "seconds": a.get("seconds")}
        status, reason = "accepted", ""
        if it["id"] in ANNOTATOR_GOLD_FIX:
            it["gold_answer"], it["gold_variants"] = ANNOTATOR_GOLD_FIX[it["id"]]
            it["notes"] = "gold corrected by annotator"
        elif it["id"] in ANNOTATOR_REJECT:
            status, reason = "rejected", "annotator: " + ANNOTATOR_REJECT[it["id"]]
        if k in REVIEW_REJECT:
            status, reason = "rejected", "review: " + REVIEW_REJECT[k]
        if k in REVIEW_GOLD_FIX:
            it["gold_answer"], it["gold_variants"] = REVIEW_GOLD_FIX[k]
            it["notes"] = "gold corrected in review"
        if k in REVIEW_ADD_VARIANTS:
            it["gold_variants"] = sorted(set(it["gold_variants"]) | set(REVIEW_ADD_VARIANTS[k]))
        if k in RETYPED and status == "accepted":
            it["notes"] = (it.get("notes", "") + "; Hinglish retyped after review").strip("; ")
        if status == "accepted" and k in NEEDS_RETYPE:
            status, reason = "needs_retype", NEEDS_RETYPE[k]
        it["status"] = status
        it["review_reason"] = reason
        if status != "accepted":
            rows.append({"position": k + 1, "id": it["id"], "status": status, "reason": reason, "en": it["en"],
                         "hi_rom_natural": it["hi_rom_natural"]})
    out = ROOT / "data" / "build" / "scriptconsist_mk_v1.jsonl"
    out.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in items) + "\n", encoding="utf-8")
    with open(ROOT / "data" / "build" / "mintaka_review.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    from collections import Counter
    c = Counter(x["status"] for x in items)
    print(dict(c))
    acc = [x for x in items if x["status"] in ("accepted", "needs_retype")]
    print("usable after retype:", len(acc), "| by domain:", dict(Counter(x["domain"] for x in acc)))


if __name__ == "__main__":
    main()
