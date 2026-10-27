"""
Freeze ScriptConsist v1: accepted Mintaka items + annotated IndicQuest items, one schema.

Inputs:  data/build/scriptconsist_mk_v1.jsonl (from finalize_mintaka.py)
         data/build/scriptconsist_iq.jsonl, data/annotations/annotations_final.jsonl
Outputs: data/scriptconsist_v1.jsonl     the benchmark (accepted items only)
         data/build/indicquest_review.csv      IndicQuest items not included, with reason

Every item has four question forms:
  en              English (source dataset)
  hi_dev          Hindi, Devanagari (Mintaka: professional translation; IndicQuest: Google MT as released)
  hi_rom_std      rule-based transliteration of hi_dev (code/romanize.py) - same words, Roman script
  hi_rom_natural  typed by a native speaker on a phone, code-mixing allowed
"""

import csv
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from romanize import romanize  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

IQ_REJECT = {
    "iq_001": "Hinglish says 'karyalay' (office) where the question says 'karyakarta' (activist)",
    "iq_017": "annotator: the flag existed only until 2019; Hinglish asks in present tense",
    "iq_109": "ambiguous: asks for the king (Shivaji) or can be read as asking for the poet (Kavindra Paramananda)",
}

# Annotation provenance (docs/PROTOCOL.md section 13): every hi_rom_natural in v1 was typed by the first
# author. A second native speaker's earlier versions of 70 items are kept separately
# (data/annotations/spelling_variation_pairs.json) for the spelling-variation analysis.

FIELDS = ["id", "source", "domain", "locality", "answer_type", "en", "hi_dev", "hi_dev_origin",
          "hi_rom_std", "hi_rom_natural", "gold_answer", "gold_variants", "sources", "notes"]


def main():
    ann = {}
    for l in open(ROOT / "data" / "annotations" / "annotations_final.jsonl", encoding="utf-8"):
        a = json.loads(l)
        ann[a["item"]] = a

    out = []
    for pos, l in enumerate(open(ROOT / "data" / "build" / "scriptconsist_mk_v1.jsonl", encoding="utf-8"), start=1):
        it = json.loads(l)
        if it["status"] != "accepted":
            continue
        it["source"], it["hi_dev_origin"] = "mintaka", "professional_translation"
        it["hi_rom_std"] = romanize(it["hi_dev"])
        it["complexity"] = it.get("complexity")
        out.append(it)

    rows = []
    for l in open(ROOT / "data" / "build" / "scriptconsist_iq.jsonl", encoding="utf-8"):
        it = json.loads(l)
        a = ann.get(it["id"])
        if a is None:
            rows.append({"id": it["id"], "reason": "not annotated (scope limited to annotated items)", "en": it["en"]})
            continue
        if it["id"] in IQ_REJECT or a.get("drop"):
            rows.append({"id": it["id"], "reason": IQ_REJECT.get(it["id"], a.get("drop_reason") or "dropped by annotator"),
                         "en": it["en"]})
            continue
        it["hi_dev"] = a.get("hi_dev") or it["hi_dev_mt"]
        it["hi_rom_natural"] = a["hi_rom_natural"]
        it["hi_rom_std"] = romanize(it["hi_dev"])
        it["source"], it["hi_dev_origin"] = "indicquest", "google_mt_as_released"
        out.append(it)

    final = []
    for it in out:
        rec = {k: it.get(k) for k in FIELDS}
        if it.get("complexity"):
            rec["complexity"] = it["complexity"]
        rec["notes"] = rec["notes"] or ""
        final.append(rec)

    (ROOT / "data" / "scriptconsist_v1.jsonl").write_text(
        "\n".join(json.dumps(x, ensure_ascii=False) for x in final) + "\n", encoding="utf-8")
    with open(ROOT / "data" / "build" / "indicquest_review.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id", "reason", "en"])
        w.writeheader()
        w.writerows(rows)

    print(f"ScriptConsist v1: {len(final)} items")
    print("  by source:", dict(Counter(x["source"] for x in final)))
    print("  by locality:", dict(Counter(x["locality"] for x in final)))
    print("  by answer type:", dict(Counter(x["answer_type"] for x in final)))
    print("  by domain:", dict(sorted(Counter(x["domain"] for x in final).items())))


if __name__ == "__main__":
    main()
