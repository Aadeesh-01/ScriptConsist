"""
Build ScriptConsist-MK: a stratified 300-question sample from Mintaka (train + test),
with professionally translated Hindi, extended with Romanized Hindi.

Source: Sen et al. (2022), Mintaka, COLING. CC BY 4.0.
        https://github.com/amazon-science/mintaka

Usage: python code/build_from_mintaka.py path/to/mintaka/data
Outputs:
  data/build/scriptconsist_mk.jsonl       300 sampled items
  data/build/mintaka_filtering.csv        counts per filter reason (train + test pool)
"""

import csv
import json
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from romanize import romanize  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SOURCE = {"title": "Mintaka (Sen et al., COLING 2022)", "url": "https://github.com/amazon-science/mintaka"}
N_TOTAL = 300
N_HELPER = 60
SEED = 2026

KEEP_TYPES = {"generic", "superlative", "intersection", "multihop", "ordinal"}
# excluded: comparative (answer is one of two options named in the question), yesno (50% baseline),
#           count / difference (numeric answers that drift over time or are ill-posed)
TEMPORAL = re.compile(r"\b(current|currently|now|today|latest|recent|recently|still|so far|as of|"
                      r"to date|yet|most recent|this year|nowadays)\b", re.I)
LATIN = re.compile(r"[A-Za-z]")
# options named in the question ("Out of Harry, Ron, and Hermione...", "X or Y") -> guessable
# "What state grows potatoes?" reads as an Indian state in Hindi -> correct Indian answers scored wrong
US_IMPLICIT = re.compile(r"\b(state|states|governor|governors|constitution|congress|senate|senator|supreme court|"
                         r"president|presidents|federal|founding fathers|union)\b", re.I)
US_EXPLICIT = re.compile(r"\b(U\.?S\.?A?|United States|America|American|Americans)\b")
# records that can be broken after Mintaka was built (2022)
DRIFTING_RECORD = re.compile(r"\b(ever|all time|all-time|in history|best[- ]selling|most money|least money|"
                             r"highest[- ]grossing|grossing|most expensive|sold the most|most popular)\b", re.I)
CHOICE = re.compile(r"\b(out of|between|or|which of)\b", re.I)
INDIA = re.compile(r"\b(India|Indian|Delhi|Mumbai|Bollywood|Hindi|Kolkata|Chennai)\b")
CATEGORY = {"movies": "Movies", "music": "Music", "sports": "Sports", "books": "Books",
            "geography": "Geography", "politics": "Politics", "videogames": "Video Games",
            "history": "History"}


def norm(s):
    return re.sub(r"[^\wऀ-ॿ]+", " ", s.lower()).strip()


def screen(q):
    """Return 'ok' or the first failing reason."""
    if q["complexityType"] not in KEEP_TYPES:
        return f"type_{q['complexityType']}"
    a = q["answer"]
    at = a["answerType"]
    if at not in ("entity", "date"):
        return f"answer_{at}"
    if at == "entity":
        if not a.get("answer") or len(a["answer"]) != 1:
            return "multi_or_no_answer"
        lab = a["answer"][0]["label"]
        if not lab.get("en") or not lab.get("hi"):
            return "no_hindi_answer_label"
    if at == "date" and (not a.get("answer") or len(a["answer"]) != 1):
        return "multi_or_no_answer"
    if TEMPORAL.search(q["question"]):
        return "temporal"
    if US_IMPLICIT.search(q["question"]) and not US_EXPLICIT.search(q["question"]):
        return "implicit_us_context"
    if DRIFTING_RECORD.search(q["question"]):
        return "drifting_record"
    if CHOICE.search(q["question"]):
        return "choice_in_question"
    hi = q["translations"].get("hi", "")
    if not hi:
        return "no_hindi"
    if LATIN.search(hi):
        return "latin_in_hindi"
    if len(q["question"].split()) > 25:
        return "too_long"
    if at == "entity":
        lab = a["answer"][0]["label"]
        if len(norm(lab["en"])) >= 4 and re.search(rf"\b{re.escape(norm(lab['en']))}\b", norm(q["question"])):
            return "answer_leak"
        if len(norm(lab["hi"])) >= 3 and norm(lab["hi"]) in norm(hi):
            return "answer_leak"
    return "ok"


def gold_of(q):
    a = q["answer"]
    if a["answerType"] == "entity":
        lab = a["answer"][0]["label"]
        variants = sorted({lab["en"], lab["hi"], a.get("mention") or lab["en"]} - {""})
        return lab["en"], variants, "entity", a["answer"][0]["name"]
    d = str(a["answer"][0])
    year = d[:4]
    variants = sorted({year, d, a.get("mention") or d})
    return year, variants, "year", None


def main(data_dir):
    data_dir = Path(data_dir)
    pool = []
    for split in ("train", "test"):
        for q in json.load(open(data_dir / f"mintaka_{split}.json", encoding="utf-8")):
            q["_split"] = split
            pool.append(q)

    reasons = Counter()
    seen = set()
    ok = []
    for q in pool:
        r = screen(q)
        if r == "ok":
            k = norm(q["question"])
            if k in seen:
                r = "duplicate"
            seen.add(k)
        reasons[r] += 1
        if r == "ok":
            ok.append(q)

    # Stratify: equal share per category; within a category ~40% generic, rest spread over complex types.
    rng = random.Random(SEED)
    by_cat = defaultdict(list)
    for q in ok:
        by_cat[q["category"]].append(q)
    cats = sorted(by_cat)
    per_cat = {c: N_TOTAL // len(cats) + (1 if i < N_TOTAL % len(cats) else 0) for i, c in enumerate(cats)}
    sample = []
    for c in cats:
        qs = by_cat[c][:]
        rng.shuffle(qs)
        n = per_cat[c]
        n_gen = round(n * 0.4)
        gen = [q for q in qs if q["complexityType"] == "generic"][:n_gen]
        rest_by_type = defaultdict(list)
        for q in qs:
            if q["complexityType"] != "generic":
                rest_by_type[q["complexityType"]].append(q)
        rest, types = [], sorted(rest_by_type)
        while len(gen) + len(rest) < n and any(rest_by_type.values()):
            for t in types:
                if rest_by_type[t] and len(gen) + len(rest) < n:
                    rest.append(rest_by_type[t].pop())
        sample.extend(gen + rest)

    sample.sort(key=lambda q: (q["category"], q["complexityType"], q["id"]))
    helper = {q["id"] for q in sample[::N_TOTAL // N_HELPER]}

    items = []
    for q in sample:
        gold, variants, atype, qid = gold_of(q)
        hi = " ".join(q["translations"]["hi"].split())
        items.append({
            "id": f"mk_{q['id']}",
            "mintaka_id": q["id"],
            "mintaka_split": q["_split"],
            "domain": CATEGORY[q["category"]],
            "complexity": q["complexityType"],
            "locality": "india" if INDIA.search(q["question"]) else "global",
            "answer_type": atype,
            "en": " ".join(q["question"].split()),
            "hi_dev_mt": "",            # not MT: professional translation
            "hi_dev_pro": hi,           # Mintaka's professional Hindi, unedited
            "hi_dev": "",               # after annotator check (usually identical to hi_dev_pro)
            "hi_rom_natural": "",
            "hi_rom_std": romanize(hi),
            "gold_answer": gold,
            "gold_variants": variants,
            "gold_wikidata": qid,
            "sources": [SOURCE],
            "provenance": "mintaka",
            "helper_subset": q["id"] in helper,
            "status": "candidate",
            "notes": "",
        })

    out = ROOT / "data" / "build" / "scriptconsist_mk.jsonl"
    out.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in items) + "\n", encoding="utf-8")
    with open(ROOT / "data" / "build" / "mintaka_filtering.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["reason", "count"])
        for r, n in reasons.most_common():
            w.writerow([r, n])

    print(f"pool (train+test): {len(pool)} | pass all filters: {len(ok)} | sampled: {len(items)}")
    print("filter reasons:", dict(reasons.most_common()))
    print("sample by domain:", dict(Counter(x["domain"] for x in items)))
    print("sample by complexity:", dict(Counter(x["complexity"] for x in items)))
    print("sample by answer type:", dict(Counter(x["answer_type"] for x in items)))
    print("sample by split:", dict(Counter(x["mintaka_split"] for x in items)))
    print("india-related:", sum(x["locality"] == "india" for x in items), "| helper subset:", len(helper))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else ROOT / "data" / "raw" / "mintaka")
