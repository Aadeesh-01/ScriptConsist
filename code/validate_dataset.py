"""
Validate ScriptConsist items against data/PROTOCOL.md.

Usage:
    python code/validate_dataset.py data/candidates.jsonl [--strict]

Accepts .jsonl (one item per line) or .json ({"questions": [...]}).
Exit code 1 if any item has an ERROR (or a WARNING with --strict).
"""

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

DOMAINS = {"History", "Geography", "Science", "Civics", "Culture", "Economy & Society",
           "Politics", "Literature", "Economics",
           "Movies", "Music", "Sports", "Books", "Video Games"}  # second line: IndicQuest domains
LOCALITY = {"india", "global"}
TIERS = {1, 2, 3}
ANSWER_TYPES = {"entity", "number", "date", "year"}
STATUSES = {"candidate", "translated", "verified", "accepted", "rejected"}
REQUIRED = ["id", "domain", "locality", "answer_type", "en",
            "gold_answer", "gold_variants", "sources", "status"]
SCRIPT_FIELDS = ["hi_dev", "hi_rom_natural", "hi_rom_std"]
QUESTION_FIELDS = ["en", "hi_dev_mt", "hi_dev_pro"] + SCRIPT_FIELDS  # required once past 'candidate'

TEMPORAL = re.compile(r"\b(current(ly)?|recent(ly)?|latest|now|today|this year|present)\b", re.I)
CONTESTED = re.compile(r"\b(considered|known as the (first|greatest|father)|regarded|best|greatest)\b", re.I)
DEVANAGARI = re.compile(r"[ऀ-ॿ]")
LATIN = re.compile(r"[A-Za-z]")


def load(path: Path):
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".jsonl":
        return [json.loads(l) for l in text.splitlines() if l.strip()]
    data = json.loads(text)
    return data["questions"] if isinstance(data, dict) else data


def norm(s: str) -> str:
    return re.sub(r"[^\wऀ-ॿ]+", " ", s.lower()).strip()


def check(item):
    errs, warns = [], []
    for k in REQUIRED:
        if k not in item or item[k] in ("", None, []):
            errs.append(f"missing {k}")
    if errs:
        return errs, warns

    if item["domain"] not in DOMAINS:
        errs.append(f"bad domain {item['domain']!r}")
    if item["locality"] not in LOCALITY:
        errs.append(f"bad locality {item['locality']!r}")
    if "tier" in item and item["tier"] not in TIERS:
        errs.append(f"bad tier {item['tier']!r}")
    if item["answer_type"] not in ANSWER_TYPES:
        errs.append(f"bad answer_type {item['answer_type']!r}")
    if item["status"] not in STATUSES:
        errs.append(f"bad status {item['status']!r}")

    # Criterion 1: short answer
    if len(item["gold_answer"].split()) > 5 and not item.get("gold_wikidata"):  # titles from Wikidata may be long
        errs.append("gold_answer longer than 5 words")

    # Criterion 2: time stability
    if TEMPORAL.search(item["en"]):
        errs.append("temporal word in question (current/recent/latest...)")

    # Criterion 3: contested phrasing (heuristic -> warning)
    if CONTESTED.search(item["en"]):
        warns.append("possibly contested phrasing ('considered', 'known as the first'...)")

    # Criterion 4: two sources with URLs
    srcs = [s for s in item["sources"] if isinstance(s, dict) and s.get("url")]
    need = 1 if item.get("provenance") in ("indicquest", "mintaka") else 2  # published benchmark counts as a verified source
    if len(srcs) < need:
        errs.append(f"needs >={need} sources with URL (has {len(srcs)})")

    # Criterion 5: scorable numbers
    if item["answer_type"] in {"number", "year"} and not re.search(r"\d", item["gold_answer"]):
        errs.append("numeric answer has no digits in gold_answer")
    if item["answer_type"] == "year" and not re.fullmatch(r"\d{3,4}( (BCE|CE))?", item["gold_answer"]):
        warns.append("year answer not in canonical 'YYYY' form")

    # Gold variants should cover Devanagari once translated
    if item["status"] != "candidate":
        for f in SCRIPT_FIELDS:
            if not item.get(f):
                errs.append(f"status={item['status']} but {f} empty")
        if item.get("hi_dev") and not DEVANAGARI.search(item["hi_dev"]):
            errs.append("hi_dev contains no Devanagari")
        for f in ("hi_rom_natural", "hi_rom_std"):
            if item.get(f) and DEVANAGARI.search(item[f]):
                errs.append(f"{f} contains Devanagari")
        if not any(DEVANAGARI.search(v) for v in item["gold_variants"]) and item["answer_type"] == "entity":
            warns.append("no Devanagari gold variant for entity answer")

    # Criterion 6: answer leakage
    gold_forms = {norm(item["gold_answer"])} | {norm(v) for v in item["gold_variants"]}
    gold_forms = {g for g in gold_forms if len(g) >= 4}
    for f in QUESTION_FIELDS:
        q = norm(item.get(f) or "")
        for g in gold_forms:
            if g and re.search(rf"\b{re.escape(g)}\b", q):
                errs.append(f"answer leaks into {f}: {g!r}")
                break
    return errs, warns


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path", type=Path)
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args()

    items = load(args.path)
    ids = Counter(i.get("id") for i in items)
    dup = {k for k, v in ids.items() if v > 1}
    en_dup = Counter(norm(i.get("en", "")) for i in items)

    n_err = n_warn = 0
    for it in items:
        errs, warns = check(it)
        if it.get("id") in dup:
            errs.append("duplicate id")
        if en_dup[norm(it.get("en", ""))] > 1:
            warns.append("duplicate English question text")
        if errs or warns:
            print(f"{it.get('id', '?')}: {it.get('en', '')[:70]}")
            for e in errs:
                print(f"   ERROR  {e}")
            for w in warns:
                print(f"   warn   {w}")
        n_err += bool(errs)
        n_warn += bool(warns)

    ok = len(items) - n_err
    print(f"\n{len(items)} items | {ok} pass | {n_err} with errors | {n_warn} with warnings")
    acc = [i for i in items if i.get("status") == "accepted"]
    if acc:
        for key in ("domain", "locality", "tier", "answer_type"):
            print(f"  {key}: {dict(Counter(i.get(key) for i in acc))}")
    sys.exit(1 if n_err or (args.strict and n_warn) else 0)


if __name__ == "__main__":
    main()
