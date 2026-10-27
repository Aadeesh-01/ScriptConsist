"""
Extend the blind validation sample (v1: 300 answers from 5 models) with
  (a) 40 answers from the two Indic models run later (Airavata, Gajendra): 20 each, 5 per form,
      half auto-correct and half auto-wrong per form;
  (b) 48 repeats of earlier items (12 per form, half auto-correct), shown again much later under a new id,
      to measure the validator's own consistency (intra-rater agreement), since there is one validator.

The first 300 items keep their ids and content. New items are mixed in at random positions; every repeat
appears at least 90 positions after its first showing.

Inputs:  results/validation/sample_key.jsonl (v1 key), results/validation/bundle_v1.json (items as shown),
         results/scored/<run>.jsonl, data/scriptconsist_v1.jsonl
Outputs: results/validation/sample_key.jsonl   (extended; adds `batch` and `repeat_of`)
         results/validation/bundle_v1.json     (extended; what the annotation page shows)
"""

import json
import random
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VAL = ROOT / "results" / "validation"
SEED = 20261027
FORMS = ["en", "hi_dev", "hi_rom_std", "hi_rom_natural"]
NEW_RUNS = ["ai4bharat__Airavata__fp16", "BhabhaAI__Gajendra-v0.1__fp16"]


def main():
    rng = random.Random(SEED)
    ds = {json.loads(l)["id"]: json.loads(l) for l in open(ROOT / "data" / "scriptconsist_v1.jsonl", encoding="utf-8")}
    key = [json.loads(l) for l in open(VAL / "sample_key.jsonl", encoding="utf-8")]
    items = json.load(open(VAL / "bundle_v1.json", encoding="utf-8"))["items"]
    key = [k for k in key if k.get("batch", "v1") == "v1"]
    items = [i for i in items if int(i["id"][1:]) <= 300]
    assert len(key) == len(items) == 300
    for k in key:
        k.setdefault("batch", "v1")
        k.setdefault("repeat_of", None)

    def shown(it, form, response):
        variants = [v for v in it["gold_variants"] if v != it["gold_answer"]]
        return {"asked": it[form], "en": it["en"], "form": form, "gold": it["gold_answer"],
                "response": response, "variants": variants}

    # (a) Indic-model answers
    new_items, new_key = [], []
    n = 300
    for r_i, run in enumerate(NEW_RUNS):
        rows = [json.loads(l) for l in open(ROOT / "results" / "scored" / f"{run}.jsonl", encoding="utf-8")]
        by = defaultdict(list)
        for r in rows:
            if r["form"] in FORMS:
                by[(r["form"], bool(r["correct"]))].append(r)
        for f_i, form in enumerate(FORMS):
            n_true = 3 if (r_i + f_i) % 2 == 0 else 2          # 5 per form per model; 5/5 per form overall
            for label, cnt in ((True, n_true), (False, 5 - n_true)):
                for r in rng.sample(by[(form, label)], cnt):
                    n += 1
                    vid = f"v{n:03d}"
                    new_items.append({"id": vid, **shown(ds[r["item"]], form, r["response"])})
                    new_key.append({"id": vid, "key": r["key"], "model": r["model"], "precision": r["precision"],
                                    "form": form, "auto_correct": bool(r["correct"]), "match_rule": r["match_rule"],
                                    "batch": "indic_models", "repeat_of": None})

    # mix the 40 into the first 300 at random positions
    seq = items[:]
    for it in new_items:
        seq.insert(rng.randrange(len(seq) + 1), it)

    # (b) repeats: sources from the first 150 positions, placed after position 240
    pos = {it["id"]: p for p, it in enumerate(seq)}
    kid = {k["id"]: k for k in key + new_key}
    early = [it for it in seq[:150] if kid[it["id"]]["batch"] == "v1"]
    sources = []
    for form in FORMS:
        for label in (True, False):
            pool = [it for it in early if it["form"] == form and kid[it["id"]]["auto_correct"] == label]
            sources += rng.sample(pool, 6)
    rng.shuffle(sources)
    for src in sources:
        n += 1
        vid = f"v{n:03d}"
        rep = {**{k: v for k, v in src.items() if k not in ("id", "order")}, "id": vid}
        lo = max(240, pos[src["id"]] + 90)
        seq.insert(rng.randrange(lo, len(seq) + 1), rep)
        pos = {it["id"]: p for p, it in enumerate(seq)}
        new_key.append({**kid[src["id"]], "id": vid, "batch": "repeat", "repeat_of": src["id"]})

    for p, it in enumerate(seq):
        it["order"] = p
    for it in seq:
        if it["id"] in {k["id"] for k in new_key if k["batch"] == "repeat"}:
            src = next(k["repeat_of"] for k in new_key if k["id"] == it["id"])
            assert pos[it["id"]] - pos[src] >= 90

    (VAL / "bundle_v1.json").write_text(json.dumps({"items": seq}, ensure_ascii=False), encoding="utf-8")
    with open(VAL / "sample_key.jsonl", "w", encoding="utf-8") as f:
        for k in key + new_key:
            f.write(json.dumps(k, ensure_ascii=False) + "\n")
    from collections import Counter
    allk = key + new_key
    print("items:", len(seq), "| by batch:", dict(Counter(k["batch"] for k in allk)))
    print("by model:", dict(Counter(k["model"] for k in allk)))
    print("indic by form/label:", dict(Counter((k["form"], k["auto_correct"]) for k in new_key if k["batch"] == "indic_models")))
    print("repeat gaps (min):", min(pos[k["id"]] - pos[k["repeat_of"]] for k in new_key if k["batch"] == "repeat"))


if __name__ == "__main__":
    main()
