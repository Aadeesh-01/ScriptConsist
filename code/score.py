"""
Score model answers against ScriptConsist gold answers, across scripts.

A model asked in Hindi may answer "मार्क ट्वैन", in Hinglish "Mark Twain", or with a sentence
("George Orwell ki mrityu 1950 mein hui thi"). The matcher accepts any of these:

  year    any 3-4 digit number in the answer (Devanagari digits converted) equals the gold year
  number  any number in the answer equals a numeric gold variant, else falls back to text matching
  entity  a gold variant (English, Devanagari, or its Roman transliteration) appears as whole words
          in the cleaned answer; else the answer's Roman transliteration contains it; else a fuzzy
          match on short answers; else the gold's distinctive last word (e.g. a surname) appears

Every decision records which rule fired (`match_rule`), so the automatic scores can be audited and
compared with human judgements before any result is reported.

Usage:
  python code/score.py results/generations/*.jsonl        -> results/scored/<same name>.jsonl + summary
"""

import json
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from romanize import romanize  # noqa: E402

try:
    from rapidfuzz import fuzz
except ImportError:  # pragma: no cover
    fuzz = None

ROOT = Path(__file__).resolve().parent.parent
DEV = re.compile(r"[ऀ-ॿ]")
DEV_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")
GENERIC_LAST = {"city", "river", "war", "party", "park", "island", "university", "movement", "empire", "game",
                "series", "cup", "award", "awards", "state", "states", "mountains", "sea", "ocean", "lake", "act",
                "soil", "rock", "glacier", "caves", "palace", "sultanate", "team", "club", "national", "of", "the",
                "kingdom", "republic", "dynasty", "civilization", "football", "association", "world", "ring",
                "king", "return", "phoenix", "prince", "azkaban", "stone", "economy", "system", "house", "brothers",
                "range", "desert", "valley", "temple", "fort", "india", "england", "america"}
PREFIXES = re.compile(r"^\s*(final answer|answer|ans|uttar|jawab|उत्तर|जवाब)\s*[:\-–]\s*", re.I)


def clean_response(r):
    """First meaningful line, without labels or markdown."""
    r = (r or "").replace("**", "").replace("__", "").strip()
    lines = [l.strip() for l in r.splitlines() if l.strip()]
    if not lines:
        return ""
    first = PREFIXES.sub("", lines[0])
    if not first and len(lines) > 1:
        first = lines[1]
    return first


def strip_accents(s):
    # Latin accents only; Devanagari combining marks (matras) must stay
    return "".join(c for c in unicodedata.normalize("NFKD", s)
                    if not (unicodedata.combining(c) and not "\u0900" <= c <= "\u097F"))


def norm(s):
    s = unicodedata.normalize("NFKC", strip_accents(s or "")).translate(DEV_DIGITS).lower()
    s = s.replace("’", "'").replace("‘", "'")
    s = re.sub(r"[^\wऀ-ॿ' ]+", " ", s)
    s = re.sub(r"\b(the|a|an)\b", " ", s)
    s = s.replace("'s", "s").replace("'", "")
    return re.sub(r"\s+", " ", s).strip()


def contains(hay, needle):
    return bool(needle) and re.search(rf"(?<![\wऀ-ॿ]){re.escape(needle)}(?![\wऀ-ॿ])", hay) is not None


def gold_forms(item):
    forms = {item["gold_answer"], *item.get("gold_variants", [])}
    out = set()
    for g in forms:
        if not g:
            continue
        out.add(norm(g))
        if DEV.search(g):
            out.add(norm(romanize(g)))
    return {g for g in out if g}


def numbers_in(s):
    s = unicodedata.normalize("NFKC", s).translate(DEV_DIGITS)
    return [n.replace(",", "") for n in re.findall(r"\d[\d,]*", s)]


STOP = {"of", "the", "and", "a", "an", "ka", "ki", "ke", "in", "on", "de", "du", "da", "s"}


def skeleton(t):
    """Consonant skeleton for comparing transliterated names: nuremberg / nyuremabarg -> nrmbrg."""
    t = t.lower()
    for a, b in (("ch", "C"), ("ph", "f"), ("bh", "b"), ("kh", "k"), ("gh", "g"), ("th", "t"), ("dh", "d"),
                 ("sh", "s"), ("ck", "k"), ("ce", "se"), ("ci", "si"), ("c", "k"), ("q", "k"), ("w", "v"), ("z", "j"), ("x", "ks"), ("C", "c")):
        t = t.replace(a, b)
    head, rest = t[:1], re.sub(r"[aeiouy]", "", t[1:])
    s = head + rest
    return re.sub(r"(.)\1+", r"\1", s)


def tok_match(rt, gt):
    if gt.isdigit() or rt.isdigit():
        return rt == gt
    if len(gt) <= 2 or len(rt) <= 2:
        return rt == gt
    r = fuzz.ratio(rt, gt)
    if r >= 80:
        return True
    if len(gt) >= 4 and r >= 75 and rt[0] == gt[0] and rt[-1] == gt[-1]:
        return True
    sk_r, sk_g = skeleton(rt), skeleton(gt)
    return len(sk_g) >= 3 and sk_r == sk_g


OPTIONAL = {"city", "river", "brothers", "mountains", "mountain", "lake", "ocean", "sea", "party", "national",
            "park", "university", "episode", "empire", "caves", "cave", "island", "desert", "glacier", "team",
            "club", "fc", "county", "republic", "kingdom", "system", "entertainment", "movement", "war",
            "nadi", "parvat", "shahar", "sagar", "dweep", "football", "association"}


def covered(gold_norm, resp_toks, question_toks=frozenset()):
    """All distinctive words of the gold appear in the answer. Descriptor words ('river', 'city') and
    words the question already contains ('Harry Potter' in 'third Harry Potter book') are optional.
    For golds with 3+ required words, the last one may be missing ('Ivan IV' for 'Ivan IV Vasilyevich')."""
    content = [t for t in gold_norm.split() if t not in STOP]
    if not content:
        return False
    in_question = lambda t: any(tok_match(t, q) for q in question_toks)
    required = [t for t in content if t not in OPTIONAL and not in_question(t)] or content
    hits = [any(tok_match(rt, gt) for rt in resp_toks) for gt in required]
    if all(hits):
        return True
    # long names: one word may be missing ('A New Hope' for 'Star Wars: Episode IV - A New Hope', 'Red Sox')
    return len(required) >= 3 and sum(hits) >= len(required) - 1


def score_one(item, response):
    """Return (correct: bool, rule: str)."""
    raw = (response or "").strip()
    if not raw:
        return False, "empty"
    ans = clean_response(raw)
    a_norm = norm(ans)
    full_norm = norm(raw)
    atype = item["answer_type"]

    if atype == "year":
        gold_year = re.sub(r"\D", "", str(item["gold_answer"]))[:4]
        years = [n for n in numbers_in(ans) if 3 <= len(n) <= 4]
        if not years:
            years = [n for n in numbers_in(raw) if 3 <= len(n) <= 4]
        return (gold_year in years, "year" if gold_year in years else ("year_wrong" if years else "no_year"))

    if atype == "number":
        golds = {re.sub(r"[^\d]", "", v) for v in [item["gold_answer"], *item.get("gold_variants", [])]
                 if re.search(r"\d", str(v))}
        nums = numbers_in(ans) or numbers_in(raw)
        if golds & set(nums):
            return True, "number"

    forms = gold_forms(item)
    a_rom = norm(romanize(ans)) if DEV.search(ans) else a_norm
    for g in sorted(forms, key=len, reverse=True):
        if len(g) < 2:
            continue
        if contains(a_norm, g):
            return True, "exact_phrase"
        if a_rom != a_norm and contains(a_rom, g):
            return True, "transliterated_phrase"
    # answer on a later line (some models restate the question first)
    for g in forms:
        if len(g) >= 4 and contains(full_norm, g) and len(full_norm.split()) <= 40:
            return True, "phrase_in_full_response"
    # every content word of some gold form is present in the answer, allowing transliteration noise
    # (James Madison / जेम्स मेडिसन -> "jems medisan"; Nuremberg / न्यूरेमबर्ग -> "nyuremabarg")
    if fuzz is not None:
        r_toks = a_rom.split()[:25]
        q_toks = frozenset(norm(item.get("en", "")).split())
        for g in forms:
            if not DEV.search(g) and covered(g, r_toks, q_toks):
                return True, "token_coverage"
        # Devanagari answer vs Devanagari gold: vowel-mark spelling variants (ट्वेन / ट्वैन)
        if DEV.search(ans):
            dev_golds = [g for g in forms if DEV.search(g) and len(g) >= 4]
            best_dev = max((fuzz.ratio(a_norm, g) for g in dev_golds), default=0)
            best_dev = max([best_dev] + [fuzz.partial_ratio(g, a_norm) for g in dev_golds if len(g) >= 6])
            gold_digits = {n for g in dev_golds for n in numbers_in(g)}
            if best_dev >= 85 and gold_digits <= set(numbers_in(ans)):
                return True, "fuzzy_devanagari"
    # distinctive last word of a multi-word gold, e.g. surname ("Hemingway" for "Ernest Hemingway")
    latin_gold = norm(item["gold_answer"])
    toks = latin_gold.split()
    if atype == "entity" and len(toks) >= 2 and len(toks[-1]) >= 5 and toks[-1] not in GENERIC_LAST:
        a_toks = a_rom.split()
        if toks[-1] in a_toks:
            k = a_toks.index(toks[-1])
            prev = a_toks[k - 1] if k > 0 else None
            # "Hemingway", "Ernest Hemingway ne..." pass; "Motilal Nehru" for Jawaharlal Nehru does not
            gold_toks = set(toks) | {t for g in forms for t in g.split()}
            if prev is None or prev in gold_toks:
                return True, "last_word"
            return False, "last_word_other_name"
    return False, "no_match"


def load_items(path=ROOT / "data" / "scriptconsist_v1.jsonl"):
    return {json.loads(l)["id"]: json.loads(l) for l in open(path, encoding="utf-8")}


def score_file(path, items, out_dir=ROOT / "results" / "scored"):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = [json.loads(l) for l in open(path, encoding="utf-8")]
    acc = defaultdict(lambda: [0, 0])
    with open(out_dir / Path(path).name, "w", encoding="utf-8") as f:
        for r in rows:
            ok, rule = score_one(items[r["item"]], r["response"])
            r["correct"], r["match_rule"] = ok, rule
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            acc[r["form"]][0] += ok
            acc[r["form"]][1] += 1
    return {k: (c, n, c / n) for k, (c, n) in acc.items()}


if __name__ == "__main__":
    items = load_items()
    for p in sys.argv[1:]:
        res = score_file(p, items)
        print(Path(p).name)
        for form, (c, n, a) in sorted(res.items()):
            print(f"  {form:15s} {a:6.1%}  ({c}/{n})")
