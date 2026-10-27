"""
Prompt wordings and evaluation rows for ScriptConsist v1.

Each question is asked in up to five forms, and the instruction around the question is written in
the same form, so nothing outside the question leaks another script:

  en             English question, English instruction
  hi_dev         Devanagari question, Devanagari instruction
  hi_rom_std     rule-based Roman transliteration of the Devanagari question AND instruction
  hi_rom_natural first author's Hinglish question, Hinglish instruction
  hi_rom_second  second native speaker's Hinglish (73 items only), Hinglish instruction

Three wordings per form (prompt_id 0-2) so results do not hinge on one template.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from romanize import romanize  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

TEMPLATES = {
    "en": [
        "Answer the following question with only the answer (a name, place, title or year). Do not explain.\n\nQuestion: {q}\nAnswer:",
        "Give a short factual answer in a few words, with no explanation.\n{q}",
        "{q}\nReply with the answer only.",
    ],
    "hi_dev": [
        "निम्नलिखित प्रश्न का केवल उत्तर दीजिए (नाम, स्थान, शीर्षक या वर्ष)। व्याख्या न करें।\n\nप्रश्न: {q}\nउत्तर:",
        "कुछ शब्दों में छोटा तथ्यात्मक उत्तर दीजिए, कोई व्याख्या नहीं।\n{q}",
        "{q}\nसिर्फ़ उत्तर लिखिए।",
    ],
    "hinglish": [
        "Neeche diye gaye question ka sirf answer do (naam, jagah, title ya saal). Explain mat karo.\n\nQuestion: {q}\nAnswer:",
        "Chhota factual answer do, bas kuch words mein, koi explanation nahi.\n{q}",
        "{q}\nSirf answer likho.",
    ],
}


def _rom_keep_space(s):
    """Romanize s but keep its leading/trailing whitespace (romanize() strips it)."""
    if not s.strip():
        return s
    lead = s[: len(s) - len(s.lstrip())]
    trail = s[len(s.rstrip()):]
    return lead + romanize(s.strip()) + trail


def _romanized_hindi_templates():
    out = []
    for t in TEMPLATES["hi_dev"]:
        lines = []
        for line in t.split("\n"):
            lines.append("{q}".join(_rom_keep_space(p) for p in line.split("{q}")))
        out.append("\n".join(lines))
    return out


TEMPLATES["hi_rom_std"] = _romanized_hindi_templates()
TEMPLATES["hi_rom_natural"] = TEMPLATES["hinglish"]
TEMPLATES["hi_rom_second"] = TEMPLATES["hinglish"]

FORMS = ["en", "hi_dev", "hi_rom_std", "hi_rom_natural", "hi_rom_second"]


def build_rows(dataset=ROOT / "data" / "scriptconsist_v1.jsonl",
               second=ROOT / "data" / "annotations" / "spelling_variation_pairs.json",
               forms=FORMS, prompt_ids=(0, 1, 2), limit=None):
    """Return a list of {key, item, form, prompt_id, prompt} dicts."""
    items = [json.loads(l) for l in open(dataset, encoding="utf-8")]
    if limit:
        items = items[:limit]
    second_q = {}
    if Path(second).exists():
        for p in json.load(open(second, encoding="utf-8"))["pairs"]:
            second_q[p["item"]] = p["second_speaker"]
    rows = []
    for it in items:
        qs = {"en": it["en"], "hi_dev": it["hi_dev"], "hi_rom_std": it["hi_rom_std"],
              "hi_rom_natural": it["hi_rom_natural"], "hi_rom_second": second_q.get(it["id"])}
        for f in forms:
            if not qs.get(f):
                continue
            for pid in prompt_ids:
                rows.append({"key": f"{it['id']}|{f}|{pid}", "item": it["id"], "form": f, "prompt_id": pid,
                             "prompt": TEMPLATES[f][pid].replace("{q}", qs[f].strip())})
    return rows


if __name__ == "__main__":
    rows = build_rows()
    from collections import Counter
    print(len(rows), dict(Counter(r["form"] for r in rows)))
    for f in FORMS:
        r = next(r for r in rows if r["form"] == f)
        print(f"--- {f}\n{r['prompt']}")
