"""
Build the ScriptConsist explorer: one self-contained web page with the benchmark, every model's real
answers, and the main results. No server or GPU needed.

Inputs:  data/scriptconsist_v1.jsonl, data/annotations/spelling_variation_pairs.json,
         results/scored/*.jsonl, results/analysis/accuracy.csv, code/prompts.py (instruction wordings)
Outputs: demo/explorer.html   page body (published as a claude.ai artifact)
         docs/index.html      same page as a full HTML document (GitHub Pages: Settings -> Pages -> /docs)

Usage: python code/build_demo.py
"""

import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from prompts import TEMPLATES  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RUNS = [  # run file stem, display name, note
    ("CohereLabs__aya-expanse-8b__fp16", "Aya-Expanse-8B", "Cohere, multilingual"),
    ("google__gemma-2-9b-it__nf4", "Gemma-2-9B", "Google, 4-bit"),
    ("meta-llama__Llama-3.1-8B-Instruct__fp16", "Llama-3.1-8B", "Meta"),
    ("Qwen__Qwen2.5-7B-Instruct__fp16", "Qwen2.5-7B", "Alibaba"),
    ("nvidia__Nemotron-4-Mini-Hindi-4B-Instruct__fp16", "Nemotron-Hindi-4B", "NVIDIA, Hindi-adapted"),
    ("BhabhaAI__Gajendra-v0.1__fp16", "Gajendra-7B", "BhabhaAI, Hindi + Hinglish"),
    ("ai4bharat__Airavata__fp16", "Airavata-7B", "AI4Bharat, Hindi"),
]
FORMS = ["en", "hi_dev", "hi_rom_std", "hi_rom_natural", "hi_rom_second"]
MAXLEN = 220


def main():
    items = [json.loads(l) for l in open(ROOT / "data" / "scriptconsist_v1.jsonl", encoding="utf-8")]
    second = {p["item"]: p["second_speaker"] for p in
              json.load(open(ROOT / "data" / "annotations" / "spelling_variation_pairs.json", encoding="utf-8"))["pairs"]}
    out_items = []
    for it in items:
        out_items.append({
            "id": it["id"], "src": it["source"], "loc": it["locality"], "dom": it["domain"],
            "q": {"en": it["en"], "hi_dev": it["hi_dev"], "hi_rom_std": it["hi_rom_std"],
                  "hi_rom_natural": it["hi_rom_natural"], **({"hi_rom_second": second[it["id"]]} if it["id"] in second else {})},
            "gold": it["gold_answer"],
            "alt": [v for v in it["gold_variants"] if v != it["gold_answer"]][:6],
        })
    answers = {}
    for stem, name, _ in RUNS:
        a = {}
        for l in open(ROOT / "results" / "scored" / f"{stem}.jsonl", encoding="utf-8"):
            r = json.loads(l)
            resp = " ".join(r["response"].split())
            if len(resp) > MAXLEN:
                resp = resp[:MAXLEN].rstrip() + "…"
            a.setdefault(r["item"], {}).setdefault(r["form"], [None, None, None])[r["prompt_id"]] = [resp, int(bool(r["correct"]))]
        answers[name] = a
    acc = {}
    names = {stem: name for stem, name, _ in RUNS}
    for r in csv.DictReader(open(ROOT / "results" / "analysis" / "accuracy.csv", encoding="utf-8")):
        if r["run"] in names:
            acc.setdefault(names[r["run"]], {})[r["form"]] = [round(100 * float(r[k]), 1) for k in ("accuracy", "ci_low", "ci_high")]
    data = {
        "items": out_items,
        "models": [{"name": n, "note": note} for _, n, note in RUNS],
        "answers": answers,
        "acc": acc,
        "templates": {f: TEMPLATES[f] for f in FORMS},
    }
    blob = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/").replace("\ufffd", "\\ufffd")
    tpl = (ROOT / "demo" / "template.html").read_text(encoding="utf-8")
    page = tpl.replace("/*__DATA__*/null", blob)
    (ROOT / "demo" / "explorer.html").write_text(page, encoding="utf-8")
    full = ("<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1, viewport-fit=cover\">\n"
            "</head>\n<body>\n" + page + "\n</body>\n</html>\n")
    (ROOT / "docs").mkdir(exist_ok=True)
    (ROOT / "docs" / "index.html").write_text(full, encoding="utf-8")
    print(f"items {len(out_items)} | models {len(RUNS)} | page {len(page.encode()) / 1e6:.2f} MB")


if __name__ == "__main__":
    main()
